"""
Master GraphRAG Data Accumulator

This module manages the centralized GraphRAG output directory that
accumulates data from all processed documents.

Structure:
./graphrag/output/
  - entities.parquet         (all entities from all documents)
  - relationships.parquet    (all relationships)
  - communities.parquet      (all communities)
  - community_reports.parquet
  - text_units.parquet
  - documents.parquet
  - covariates.parquet
  - lancedb/                 (master vector store with embeddings)

Each document processing adds to these master files.
"""

import pandas as pd
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MasterGraphRAGAccumulator:
    """Manages centralized GraphRAG output that accumulates all document data"""

    def __init__(self, master_dir: Path = None):
        """Initialize master GraphRAG accumulator"""
        self.master_dir = master_dir or Path("./graphrag")
        self.output_dir = self.master_dir / "output"
        self.lancedb_dir = self.output_dir / "lancedb"

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lancedb_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"✅ Master GraphRAG directory: {self.master_dir.absolute()}")

    def merge_workspace_to_master(self, workspace_path: Path) -> dict:
        """
        Merge workspace output into master graphrag/output directory

        First document: MOVE workspace output to master (creates structure)
        Subsequent documents: APPEND data to existing master files

        Args:
            workspace_path: Path to workspace (e.g., workspaces/doc_xyz/)

        Returns:
            dict with merge statistics
        """
        workspace_output = workspace_path / "output"

        if not workspace_output.exists():
            logger.error(f"❌ Workspace output not found: {workspace_output}")
            return {"status": "error", "message": "Workspace output not found"}

        # Check if master output is empty (first document)
        is_first_document = self._is_master_empty()

        if is_first_document:
            logger.info("📦 First document - Moving workspace output to master directory")
            return self._move_to_master(workspace_output)
        else:
            logger.info("📊 Updating master - Appending new data to existing files")
            return self._append_to_master(workspace_output)

    def _is_master_empty(self) -> bool:
        """Check if master output directory is empty"""
        if not self.output_dir.exists():
            return True

        # Check if any parquet files exist
        parquet_files = list(self.output_dir.glob("*.parquet"))
        return len(parquet_files) == 0

    def _move_to_master(self, workspace_output: Path) -> dict:
        """
        Move workspace output to master (first document)

        This preserves the exact GraphRAG structure
        """
        try:
            logger.info(f"🚚 Moving {workspace_output} → {self.output_dir}")

            # Ensure master directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from workspace to master
            for item in workspace_output.iterdir():
                dest = self.output_dir / item.name

                if item.is_file():
                    shutil.copy2(item, dest)
                    logger.info(f"  ✅ Copied {item.name}")
                elif item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                    logger.info(f"  ✅ Copied directory {item.name}/")

            # Count what was moved
            stats = self._count_master_data()

            logger.info(f"✅ Master directory initialized: {stats['entities']}E, "
                       f"{stats['relationships']}R, {stats['communities']}C")

            return {
                "status": "success",
                "action": "initialized",
                "entities_added": stats['entities'],
                "relationships_added": stats['relationships'],
                "communities_added": stats['communities'],
                "text_units_added": stats['text_units']
            }

        except Exception as e:
            logger.error(f"❌ Error moving to master: {e}")
            return {"status": "error", "message": str(e)}

    def _append_to_master(self, workspace_output: Path) -> dict:
        """
        Append workspace data to existing master files

        This updates existing parquet files by adding new data
        """
        stats = {
            "status": "success",
            "action": "updated",
            "merged_files": [],
            "entities_added": 0,
            "relationships_added": 0,
            "communities_added": 0,
            "text_units_added": 0,
        }

        # Files to update
        parquet_files = [
            "entities.parquet",
            "relationships.parquet",
            "communities.parquet",
            "community_reports.parquet",
            "text_units.parquet",
            "documents.parquet",
            "covariates.parquet"
        ]

        for filename in parquet_files:
            workspace_file = workspace_output / filename
            master_file = self.output_dir / filename

            if not workspace_file.exists():
                logger.debug(f"⏭️  Skipping {filename} (not in workspace)")
                continue

            try:
                # Read workspace data
                workspace_df = pd.read_parquet(workspace_file)
                logger.info(f"📄 Read {filename}: {len(workspace_df)} rows from workspace")

                if not master_file.exists():
                    # Master file doesn't exist - create it
                    workspace_df.to_parquet(master_file)
                    logger.info(f"✨ Created new master {filename}")
                    added = len(workspace_df)
                else:
                    # Append to existing master file
                    master_df = pd.read_parquet(master_file)
                    logger.info(f"📄 Existing master {filename}: {len(master_df)} rows")

                    # Combine (avoid duplicates by ID if possible)
                    combined_df = self._merge_dataframes(master_df, workspace_df, filename)

                    logger.info(f"📊 Combined {filename}: {len(combined_df)} rows")

                    # Save combined data
                    combined_df.to_parquet(master_file)
                    added = len(combined_df) - len(master_df)

                # Update stats
                stats["merged_files"].append(filename)

                if filename == "entities.parquet":
                    stats["entities_added"] = added
                elif filename == "relationships.parquet":
                    stats["relationships_added"] = added
                elif filename == "communities.parquet":
                    stats["communities_added"] = added
                elif filename == "text_units.parquet":
                    stats["text_units_added"] = added

                logger.info(f"✅ Updated {filename}: +{added} new rows")

            except Exception as e:
                logger.error(f"❌ Error updating {filename}: {e}")
                stats["status"] = "partial"

        # Merge LanceDB vector stores
        workspace_lancedb = workspace_output / "lancedb"
        if workspace_lancedb.exists():
            self._merge_lancedb(workspace_lancedb)

        return stats

    def _count_master_data(self) -> dict:
        """Count data in master files"""
        counts = {
            "entities": 0,
            "relationships": 0,
            "communities": 0,
            "text_units": 0
        }

        try:
            if (self.output_dir / "entities.parquet").exists():
                df = pd.read_parquet(self.output_dir / "entities.parquet")
                counts["entities"] = len(df)

            if (self.output_dir / "relationships.parquet").exists():
                df = pd.read_parquet(self.output_dir / "relationships.parquet")
                counts["relationships"] = len(df)

            if (self.output_dir / "communities.parquet").exists():
                df = pd.read_parquet(self.output_dir / "communities.parquet")
                counts["communities"] = len(df)

            if (self.output_dir / "text_units.parquet").exists():
                df = pd.read_parquet(self.output_dir / "text_units.parquet")
                counts["text_units"] = len(df)
        except:
            pass

        return counts

    def _merge_dataframes(self, master_df: pd.DataFrame, workspace_df: pd.DataFrame,
                         filename: str) -> pd.DataFrame:
        """
        Merge workspace data into master, avoiding duplicates

        Uses 'id' column if available to detect duplicates
        """
        # Try to find ID column
        id_col = None
        for possible_id in ['id', 'entity_id', 'relationship_id', 'community_id', 'text_unit_id']:
            if possible_id in workspace_df.columns:
                id_col = possible_id
                break

        if id_col and id_col in master_df.columns:
            # Remove duplicates from workspace (keep master version)
            existing_ids = set(master_df[id_col])
            new_rows = workspace_df[~workspace_df[id_col].isin(existing_ids)]

            if len(new_rows) < len(workspace_df):
                duplicates = len(workspace_df) - len(new_rows)
                logger.info(f"⚠️  Filtered {duplicates} duplicates from {filename}")

            # Concatenate
            combined = pd.concat([master_df, new_rows], ignore_index=True)
        else:
            # No ID column - just append (may create duplicates)
            logger.warning(f"⚠️  No ID column found in {filename}, appending all rows")
            combined = pd.concat([master_df, workspace_df], ignore_index=True)

        return combined

    def _merge_lancedb(self, workspace_lancedb: Path):
        """
        Merge workspace LanceDB vector store into master

        This copies embedding data to the master vector store
        """
        if not workspace_lancedb.exists():
            logger.warning("⏭️  No workspace LanceDB to merge")
            return

        try:
            import lancedb

            # Connect to both databases
            workspace_db = lancedb.connect(str(workspace_lancedb))
            master_db = lancedb.connect(str(self.lancedb_dir))

            workspace_tables = workspace_db.table_names()
            logger.info(f"🔍 Found {len(workspace_tables)} tables in workspace LanceDB")

            for table_name in workspace_tables:
                try:
                    workspace_table = workspace_db.open_table(table_name)
                    count = workspace_table.count_rows()

                    if count == 0:
                        logger.info(f"⏭️  Skipping empty table: {table_name}")
                        continue

                    logger.info(f"📊 Merging table: {table_name} ({count} rows)")

                    # Read workspace data
                    df = workspace_table.to_pandas()

                    # Merge with master
                    if table_name in master_db.table_names():
                        # Append to existing
                        master_table = master_db.open_table(table_name)
                        master_df = master_table.to_pandas()

                        # Combine
                        combined_df = pd.concat([master_df, df], ignore_index=True)

                        # Drop duplicates based on ID columns only (not vector columns)
                        # Find potential ID columns (avoid numpy arrays/vectors)
                        id_columns = []
                        for col in combined_df.columns:
                            # Skip columns that contain numpy arrays (vectors/embeddings)
                            if len(combined_df) > 0:
                                sample_value = combined_df[col].iloc[0]
                                if not isinstance(sample_value, (list, tuple)) and \
                                   not (hasattr(sample_value, '__array__') and hasattr(sample_value, 'shape')):
                                    id_columns.append(col)

                        # Deduplicate based on non-vector columns
                        if id_columns:
                            initial_count = len(combined_df)
                            combined_df = combined_df.drop_duplicates(subset=id_columns, keep='first')
                            duplicates_removed = initial_count - len(combined_df)
                            if duplicates_removed > 0:
                                logger.info(f"🔄 Removed {duplicates_removed} duplicate rows from {table_name}")
                        else:
                            logger.warning(f"⚠️  No suitable deduplication columns found for {table_name}, keeping all rows")

                        # Recreate table
                        master_db.drop_table(table_name)
                        master_db.create_table(table_name, data=combined_df)

                        logger.info(f"✅ Merged {table_name}: {len(master_df)} + {len(df)} = {len(combined_df)} rows")
                    else:
                        # Create new table
                        master_db.create_table(table_name, data=df)
                        logger.info(f"✨ Created new master table: {table_name}")

                except Exception as e:
                    logger.error(f"❌ Error merging LanceDB table {table_name}: {e}")

            logger.info("✅ LanceDB merge complete")

        except Exception as e:
            logger.error(f"❌ LanceDB merge failed: {e}")

    def get_master_files_status(self) -> dict:
        """Get status of master parquet files"""
        status = {
            "master_dir": str(self.master_dir.absolute()),
            "output_dir": str(self.output_dir.absolute()),
            "files": {}
        }

        parquet_files = [
            "entities.parquet",
            "relationships.parquet",
            "communities.parquet",
            "community_reports.parquet",
            "text_units.parquet",
            "documents.parquet",
            "covariates.parquet"
        ]

        for filename in parquet_files:
            filepath = self.output_dir / filename
            if filepath.exists():
                try:
                    df = pd.read_parquet(filepath)
                    status["files"][filename] = {
                        "exists": True,
                        "rows": len(df),
                        "columns": len(df.columns)
                    }
                except:
                    status["files"][filename] = {"exists": True, "error": "Cannot read"}
            else:
                status["files"][filename] = {"exists": False}

        # Check LanceDB
        if self.lancedb_dir.exists():
            try:
                import lancedb
                db = lancedb.connect(str(self.lancedb_dir))
                status["lancedb_tables"] = db.table_names()
            except:
                status["lancedb_tables"] = []

        return status
