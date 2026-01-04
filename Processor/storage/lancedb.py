"""
Enhanced LanceDB Storage Implementation with Direct Parquet Support

"""

import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LanceDBStorage:
    """Enhanced LanceDB storage for GraphRAG data with direct parquet support"""
    
    def __init__(self, db_path: str = "./lancedb_graphrag"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = None
        self.tables = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize LanceDB connection"""
        try:
            import lancedb
            import pyarrow as pa
            import pandas as pd
            self.db = lancedb.connect(str(self.db_path))
            self.pa = pa
            self.pd = pd
            logger.info(f"✅ LanceDB connected: {self.db_path}")
            self._init_tables()
        except ImportError as e:
            logger.error(f"❌ Required packages not installed. Install with: pip install lancedb pyarrow pandas")
            raise
        except Exception as e:
            logger.error(f"❌ LanceDB initialization failed: {e}")
            raise
    
    def _init_tables(self):
        """Initialize required tables with normalized schemas including vector embeddings"""
        try:
            # Documents table - updated with more counts
            if "documents" not in self.db.table_names():
                documents_schema = self.pa.schema([
                    self.pa.field("document_id", self.pa.string()),
                    self.pa.field("filename", self.pa.string()),
                    self.pa.field("bucket", self.pa.string()),
                    self.pa.field("source_url", self.pa.string()),
                    self.pa.field("processing_timestamp", self.pa.timestamp('us')),
                    self.pa.field("entities_count", self.pa.int32()),
                    self.pa.field("relationships_count", self.pa.int32()),
                    self.pa.field("communities_count", self.pa.int32()),
                    self.pa.field("claims_count", self.pa.int32()),
                    self.pa.field("covariates_count", self.pa.int32()),
                    self.pa.field("text_units_count", self.pa.int32())
                ])

                empty_data = self.pa.table({
                    "document_id": [],
                    "filename": [],
                    "bucket": [],
                    "source_url": [],
                    "processing_timestamp": [],
                    "entities_count": [],
                    "relationships_count": [],
                    "communities_count": [],
                    "claims_count": [],
                    "covariates_count": [],
                    "text_units_count": []
                }, schema=documents_schema)

                self.tables["documents"] = self.db.create_table("documents", empty_data)
            else:
                self.tables["documents"] = self.db.open_table("documents")

            # Initialize all tables including new ones
            self._init_entities_table()
            self._init_relationships_table()
            self._init_communities_table()
            self._init_claims_table()
            self._init_covariates_table()
            self._init_text_units_table()

            logger.info("✅ LanceDB tables initialized successfully")

        except Exception as e:
            logger.error(f"❌ Table initialization failed: {e}")
            raise
    
    def _init_entities_table(self):
        """Initialize entities table with optional vector embeddings (1536D for nomic-embed-text)"""
        if "entities" not in self.db.table_names():
            entities_schema = self.pa.schema([
                self.pa.field("entity_id", self.pa.string()),
                self.pa.field("name", self.pa.string()),
                self.pa.field("type", self.pa.string()),
                self.pa.field("description", self.pa.string()),
                self.pa.field("document_id", self.pa.string()),
                self.pa.field("degree", self.pa.int32()),
                self.pa.field("rank", self.pa.float32()),
                # Vector embedding for semantic search (768D for nomic-embed-text)
                self.pa.field("description_embedding", self.pa.list_(self.pa.float32(), 768))
            ])

            empty_data = self.pa.table({
                "entity_id": [],
                "name": [],
                "type": [],
                "description": [],
                "document_id": [],
                "degree": [],
                "rank": [],
                "description_embedding": []
            }, schema=entities_schema)

            self.tables["entities"] = self.db.create_table("entities", empty_data)
            # Create vector index on description_embedding for fast similarity search
            try:
                self.tables["entities"].create_index(
                    vector_column_name="description_embedding",
                    metric="cosine"
                )
                logger.info("✅ Created vector index on entities.description_embedding")
            except Exception as e:
                logger.warning(f"⚠️ Could not create vector index on entities: {e}")
        else:
            self.tables["entities"] = self.db.open_table("entities")
    
    def _init_relationships_table(self):
        """Initialize relationships table"""
        if "relationships" not in self.db.table_names():
            relationships_schema = self.pa.schema([
                self.pa.field("relationship_id", self.pa.string()),
                self.pa.field("source_entity", self.pa.string()),
                self.pa.field("target_entity", self.pa.string()),
                self.pa.field("description", self.pa.string()),
                self.pa.field("strength", self.pa.float32()),
                self.pa.field("document_id", self.pa.string()),
                self.pa.field("rank", self.pa.float32())
            ])
            
            empty_data = self.pa.table({
                "relationship_id": [],
                "source_entity": [],
                "target_entity": [],
                "description": [],
                "strength": [],
                "document_id": [],
                "rank": []
            }, schema=relationships_schema)
            
            self.tables["relationships"] = self.db.create_table("relationships", empty_data)
        else:
            self.tables["relationships"] = self.db.open_table("relationships")
    
    def _init_communities_table(self):
        """Initialize communities table"""
        if "communities" not in self.db.table_names():
            communities_schema = self.pa.schema([
                self.pa.field("community_id", self.pa.string()),
                self.pa.field("community", self.pa.int32()),
                self.pa.field("title", self.pa.string()),
                self.pa.field("summary", self.pa.string()),
                self.pa.field("member_entities", self.pa.string()),
                self.pa.field("member_count", self.pa.int32()),
                self.pa.field("rating", self.pa.float32()),
                self.pa.field("document_id", self.pa.string()),
                self.pa.field("level", self.pa.int32())
            ])

            empty_data = self.pa.table({
                "community_id": [],
                "community": [],
                "title": [],
                "summary": [],
                "member_entities": [],
                "member_count": [],
                "rating": [],
                "document_id": [],
                "level": []
            }, schema=communities_schema)

            self.tables["communities"] = self.db.create_table("communities", empty_data)
        else:
            self.tables["communities"] = self.db.open_table("communities")

    def _init_claims_table(self):
        """Initialize claims table for factual claims extraction"""
        if "claims" not in self.db.table_names():
            claims_schema = self.pa.schema([
                self.pa.field("claim_id", self.pa.string()),
                self.pa.field("subject", self.pa.string()),
                self.pa.field("object", self.pa.string()),
                self.pa.field("type", self.pa.string()),
                self.pa.field("status", self.pa.string()),
                self.pa.field("description", self.pa.string()),
                self.pa.field("source_text", self.pa.string()),
                self.pa.field("start_date", self.pa.string()),
                self.pa.field("end_date", self.pa.string()),
                self.pa.field("document_id", self.pa.string())
            ])

            empty_data = self.pa.table({
                "claim_id": [],
                "subject": [],
                "object": [],
                "type": [],
                "status": [],
                "description": [],
                "source_text": [],
                "start_date": [],
                "end_date": [],
                "document_id": []
            }, schema=claims_schema)

            self.tables["claims"] = self.db.create_table("claims", empty_data)
        else:
            self.tables["claims"] = self.db.open_table("claims")

    def _init_covariates_table(self):
        """Initialize covariates table for contextual information"""
        if "covariates" not in self.db.table_names():
            covariates_schema = self.pa.schema([
                self.pa.field("covariate_id", self.pa.string()),
                self.pa.field("subject_id", self.pa.string()),
                self.pa.field("subject_type", self.pa.string()),
                self.pa.field("covariate_type", self.pa.string()),
                self.pa.field("text_unit_id", self.pa.string()),
                self.pa.field("document_id", self.pa.string()),
                self.pa.field("attributes", self.pa.string())  # JSON string
            ])

            empty_data = self.pa.table({
                "covariate_id": [],
                "subject_id": [],
                "subject_type": [],
                "covariate_type": [],
                "text_unit_id": [],
                "document_id": [],
                "attributes": []
            }, schema=covariates_schema)

            self.tables["covariates"] = self.db.create_table("covariates", empty_data)
        else:
            self.tables["covariates"] = self.db.open_table("covariates")

    def _init_text_units_table(self):
        """Initialize text units table for document chunks with embeddings"""
        if "text_units" not in self.db.table_names():
            text_units_schema = self.pa.schema([
                self.pa.field("text_unit_id", self.pa.string()),
                self.pa.field("text", self.pa.string()),
                self.pa.field("n_tokens", self.pa.int32()),
                self.pa.field("document_id", self.pa.string()),
                self.pa.field("chunk_id", self.pa.string()),
                self.pa.field("text_embedding", self.pa.list_(self.pa.float32(), 768)),
                self.pa.field("entity_ids", self.pa.string()),  # JSON string of entity IDs
                self.pa.field("relationship_ids", self.pa.string())  # JSON string of relationship IDs
            ])

            empty_data = self.pa.table({
                "text_unit_id": [],
                "text": [],
                "n_tokens": [],
                "document_id": [],
                "chunk_id": [],
                "text_embedding": [],
                "entity_ids": [],
                "relationship_ids": []
            }, schema=text_units_schema)

            self.tables["text_units"] = self.db.create_table("text_units", empty_data)
            # Create vector index on text_embedding for fast similarity search
            try:
                self.tables["text_units"].create_index(
                    vector_column_name="text_embedding",
                    metric="cosine"
                )
                logger.info("✅ Created vector index on text_units.text_embedding")
            except Exception as e:
                logger.warning(f"⚠️ Could not create vector index on text_units: {e}")
        else:
            self.tables["text_units"] = self.db.open_table("text_units")

    def health_check(self) -> bool:
        """Check LanceDB health"""
        try:
            # Check if database is initialized
            if self.db is None:
                logger.debug("LanceDB health check failed: db is None")
                return False

            # Try to list tables to verify connection works
            try:
                _ = self.db.table_names()
                return True
            except Exception as table_error:
                # If we can't list tables, try to reconnect
                logger.debug(f"LanceDB table listing failed, attempting reconnect: {table_error}")
                try:
                    import lancedb
                    self.db = lancedb.connect(str(self.db_path))
                    _ = self.db.table_names()
                    logger.info("✅ LanceDB reconnected successfully")
                    return True
                except Exception as reconnect_error:
                    logger.debug(f"LanceDB reconnect failed: {reconnect_error}")
                    return False

        except Exception as e:
            logger.debug(f"LanceDB health check failed: {e}")
            return False

    def store_graphrag_data_from_parquet(self, artifacts_dir: Path, filename: str,
                                       bucket: str, source_url: str = "") -> str:
        """
        Store GraphRAG data directly from parquet files - MAIN METHOD

        """
        try:
            document_id = str(uuid.uuid4())
            timestamp = datetime.now()

            logger.info(f"📊 Starting parquet data transfer for {filename}")
            logger.info(f"📂 Artifacts directory: {artifacts_dir}")

            # Check for new format first
            entities_file = artifacts_dir / "entities.parquet"
            relationships_file = artifacts_dir / "relationships.parquet"
            communities_file = artifacts_dir / "communities.parquet"
            community_reports_file = artifacts_dir / "community_reports.parquet"
            covariates_file = artifacts_dir / "covariates.parquet"
            text_units_file = artifacts_dir / "text_units.parquet"

            # Fallback to old format if new format not found
            if not entities_file.exists():
                entities_file = artifacts_dir / "create_final_entities.parquet"
            if not relationships_file.exists():
                relationships_file = artifacts_dir / "create_final_relationships.parquet"
            if not communities_file.exists():
                communities_file = artifacts_dir / "create_final_communities.parquet"
            if not community_reports_file.exists():
                community_reports_file = artifacts_dir / "create_final_community_reports.parquet"
            if not covariates_file.exists():
                covariates_file = artifacts_dir / "create_final_covariates.parquet"
            if not text_units_file.exists():
                text_units_file = artifacts_dir / "create_final_text_units.parquet"

            # Load parquet files safely
            entities_df = self._load_parquet_safe(entities_file)
            relationships_df = self._load_parquet_safe(relationships_file)
            communities_df = self._load_parquet_safe(communities_file)
            community_reports_df = self._load_parquet_safe(community_reports_file)
            covariates_df = self._load_parquet_safe(covariates_file)
            text_units_df = self._load_parquet_safe(text_units_file)

            # Extract claims from covariates (GraphRAG stores claims as a type of covariate)
            claims_df = None
            if covariates_df is not None and not covariates_df.empty:
                # Try to filter claims based on common covariate_type patterns
                if 'covariate_type' in covariates_df.columns:
                    # Claims typically have covariate_type containing 'claim'
                    claims_df = covariates_df[
                        covariates_df['covariate_type'].str.lower().str.contains('claim', na=False)
                    ]
                    if not claims_df.empty:
                        logger.info(f"📋 Extracted {len(claims_df)} claims from covariates")
                    else:
                        logger.info("ℹ️ No claim-type covariates found in covariates data")
                        claims_df = None

            # Count records
            entities_count = len(entities_df) if entities_df is not None else 0
            relationships_count = len(relationships_df) if relationships_df is not None else 0
            communities_count = len(communities_df) if communities_df is not None else 0
            claims_count = len(claims_df) if claims_df is not None else 0
            covariates_count = len(covariates_df) if covariates_df is not None else 0
            text_units_count = len(text_units_df) if text_units_df is not None else 0
            
            # Store document record first
            doc_data = self.pa.table({
                "document_id": [document_id],
                "filename": [filename],
                "bucket": [bucket],
                "source_url": [source_url or filename],
                "processing_timestamp": [timestamp],
                "entities_count": [entities_count],
                "relationships_count": [relationships_count],
                "communities_count": [communities_count],
                "claims_count": [claims_count],
                "covariates_count": [covariates_count],
                "text_units_count": [text_units_count]
            })
            self.tables["documents"].add(doc_data)
            logger.info(f"✅ Document record stored: {document_id}")
            
            # Store entities
            if entities_df is not None and not entities_df.empty:
                entities_processed = self._process_entities_dataframe(entities_df, document_id)
                if entities_processed is not None and len(entities_processed) > 0:
                    self.tables["entities"].add(entities_processed)
                    logger.info(f"✅ Stored {len(entities_processed)} entities")
                else:
                    logger.warning("⚠️ No valid entities to store")
            else:
                logger.warning("⚠️ No entities data found")
            
            # Store relationships
            if relationships_df is not None and not relationships_df.empty:
                relationships_processed = self._process_relationships_dataframe(relationships_df, document_id)
                if relationships_processed is not None and len(relationships_processed) > 0:
                    self.tables["relationships"].add(relationships_processed)
                    logger.info(f"✅ Stored {len(relationships_processed)} relationships")
                else:
                    logger.warning("⚠️ No valid relationships to store")
            else:
                logger.warning("⚠️ No relationships data found")
            
            # Store communities (merge with community_reports for summaries)
            if communities_df is not None and not communities_df.empty:
                communities_processed = self._process_communities_dataframe(
                    communities_df, community_reports_df, document_id
                )
                if communities_processed is not None and len(communities_processed) > 0:
                    self.tables["communities"].add(communities_processed)
                    logger.info(f"✅ Stored {len(communities_processed)} communities")
                else:
                    logger.warning("⚠️ No valid communities to store")
            else:
                logger.warning("⚠️ No communities data found")

            # Store claims
            if claims_df is not None and not claims_df.empty:
                claims_processed = self._process_claims_dataframe(claims_df, document_id)
                if claims_processed is not None and len(claims_processed) > 0:
                    self.tables["claims"].add(claims_processed)
                    logger.info(f"✅ Stored {len(claims_processed)} claims")
                else:
                    logger.warning("⚠️ No valid claims to store")
            else:
                logger.warning("⚠️ No claims data found")

            # Store covariates
            if covariates_df is not None and not covariates_df.empty:
                covariates_processed = self._process_covariates_dataframe(covariates_df, document_id)
                if covariates_processed is not None and len(covariates_processed) > 0:
                    self.tables["covariates"].add(covariates_processed)
                    logger.info(f"✅ Stored {len(covariates_processed)} covariates")
                else:
                    logger.warning("⚠️ No valid covariates to store")
            else:
                logger.warning("⚠️ No covariates data found")

            # Store text units
            if text_units_df is not None and not text_units_df.empty:
                text_units_processed = self._process_text_units_dataframe(text_units_df, document_id)
                if text_units_processed is not None and len(text_units_processed) > 0:
                    self.tables["text_units"].add(text_units_processed)
                    logger.info(f"✅ Stored {len(text_units_processed)} text units")
                else:
                    logger.warning("⚠️ No valid text units to store")
            else:
                logger.warning("⚠️ No text units data found")

            logger.info(f"✅ Complete GraphRAG data transfer completed for {filename}")
            logger.info(f"📊 Summary: {entities_count}E, {relationships_count}R, {communities_count}C, {claims_count}Claims, {covariates_count}Cov, {text_units_count}TU")

            return document_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store GraphRAG data from parquet: {e}")
            raise
    
    def _load_parquet_safe(self, file_path: Path) -> Optional[Any]:
        """Safely load parquet file"""
        try:
            if file_path.exists():
                df = self.pd.read_parquet(file_path)
                logger.info(f"📄 Loaded {file_path.name}: {len(df)} records")
                return df
            else:
                logger.warning(f"⚠️ File not found: {file_path.name}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to load {file_path.name}: {e}")
            return None
    
    def _process_entities_dataframe(self, df: Any, document_id: str) -> Any:
        """Process entities dataframe for LanceDB storage"""
        try:
            logger.info(f"🔄 Processing {len(df)} entities")
            
            # Reset index to ensure we have clean integer indices
            df = df.reset_index(drop=True)
            
            # Create a clean copy with required columns
            processed_df = self.pd.DataFrame()
            
            # Map GraphRAG columns to our schema with flexible column mapping
            processed_df['entity_id'] = df.get('id', df.index.astype(str)).astype(str)
            
            # Handle name/title mapping
            if 'title' in df.columns:
                name_series = df['title']
            elif 'name' in df.columns:
                name_series = df['name']
            elif 'entity' in df.columns:
                name_series = df['entity']
            else:
                name_series = self.pd.Series(['Unknown Entity'] * len(df))
            
            # Clean name series
            processed_df['name'] = name_series.fillna('').astype(str).str.strip()
            
            # Handle type mapping
            if 'type' in df.columns:
                type_series = df['type']
            else:
                type_series = self.pd.Series(['ENTITY'] * len(df))
            
            processed_df['type'] = type_series.fillna('ENTITY').astype(str).str.strip().str.upper()
            
            # Handle description mapping
            if 'description' in df.columns:
                desc_series = df['description']
            elif 'summary' in df.columns:
                desc_series = df['summary']
            else:
                desc_series = self.pd.Series([''] * len(df))

            processed_df['description'] = desc_series.fillna('').astype(str).str.strip()

            processed_df['document_id'] = document_id

            # Handle community assignment from GraphRAG (entities have community_ids field)
            if 'community_ids' in df.columns:
                # Store the community IDs as JSON string
                processed_df['community_ids'] = df['community_ids'].apply(
                    lambda x: json.dumps(x) if isinstance(x, list) else (str(x) if x is not None else '[]')
                )
                logger.info(f"✅ Entity community assignments found")
            elif 'community' in df.columns:
                # Single community ID
                processed_df['community_ids'] = df['community'].apply(
                    lambda x: json.dumps([int(x)]) if x is not None and not self.pd.isna(x) else '[]'
                )
                logger.info(f"✅ Entity community assignments found (single community)")
            else:
                processed_df['community_ids'] = '[]'
                logger.warning("⚠️ No community_ids or community column found in entities")

            # Handle description_embedding - convert to list format for LanceDB
            if 'description_embedding' in df.columns:
                # Process embeddings - they might be in various formats
                def safe_convert_embedding(emb):
                    if emb is None or (isinstance(emb, float) and self.pd.isna(emb)):
                        return [0.0] * 768  # Default zero vector
                    elif isinstance(emb, list):
                        return emb[:768] if len(emb) >= 768 else emb + [0.0] * (768 - len(emb))
                    elif isinstance(emb, str):
                        try:
                            import json
                            parsed = json.loads(emb)
                            return parsed[:768] if len(parsed) >= 768 else parsed + [0.0] * (768 - len(parsed))
                        except:
                            return [0.0] * 768
                    else:
                        return [0.0] * 768

                processed_df['description_embedding'] = df['description_embedding'].apply(safe_convert_embedding)
                logger.info("✅ Entity embeddings found and processed")
            else:
                # No embeddings available - use zero vectors
                logger.warning("⚠️ No description_embedding column found in entities - using zero vectors. Vector search will not work properly!")
                logger.warning("⚠️ To enable vector search, ensure GraphRAG is configured to generate embeddings")
                processed_df['description_embedding'] = [[0.0] * 768] * len(processed_df)
            
            # Handle degree - be more careful with data types
            if 'degree' in df.columns:
                degree_series = df['degree'].fillna(0)
                # Convert to numeric, coercing errors to 0
                degree_series = self.pd.to_numeric(degree_series, errors='coerce').fillna(0)
                processed_df['degree'] = degree_series.astype(int)
            else:
                processed_df['degree'] = 0
            
            # Handle rank - be more careful with data types
            if 'rank' in df.columns:
                rank_series = df['rank'].fillna(0.0)
                # Convert to numeric, coercing errors to 0.0
                rank_series = self.pd.to_numeric(rank_series, errors='coerce').fillna(0.0)
                processed_df['rank'] = rank_series.astype(float)
            else:
                processed_df['rank'] = 0.0
            
            # Filter out empty names
            processed_df = processed_df[processed_df['name'] != '']
            processed_df = processed_df[processed_df['name'] != 'Unknown Entity']
            
            if processed_df.empty:
                logger.warning("⚠️ No valid entities after processing")
                return None
            
            logger.info(f"✅ Processed {len(processed_df)} valid entities")
            
            # Convert to PyArrow table
            return self.pa.Table.from_pandas(processed_df)
            
        except Exception as e:
            logger.error(f"❌ Failed to process entities dataframe: {e}")
            logger.error(f"📋 Entity DataFrame columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            logger.error(f"📋 Entity DataFrame shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            return None
    
    def _process_relationships_dataframe(self, df: Any, document_id: str) -> Any:
        """Process relationships dataframe for LanceDB storage"""
        try:
            logger.info(f"🔄 Processing {len(df)} relationships")
            
            # Reset index to ensure we have clean integer indices
            df = df.reset_index(drop=True)
            
            processed_df = self.pd.DataFrame()
            
            # Map GraphRAG columns to our schema
            processed_df['relationship_id'] = df.get('id', df.index.astype(str)).astype(str)
            
            # Handle source entity mapping
            if 'source' in df.columns:
                source_series = df['source']
            elif 'source_id' in df.columns:
                source_series = df['source_id']
            else:
                logger.error("❌ No source entity column found")
                return None
            
            processed_df['source_entity'] = source_series.fillna('').astype(str).str.strip()
            
            # Handle target entity mapping
            if 'target' in df.columns:
                target_series = df['target']
            elif 'target_id' in df.columns:
                target_series = df['target_id']
            else:
                logger.error("❌ No target entity column found")
                return None
            
            processed_df['target_entity'] = target_series.fillna('').astype(str).str.strip()
            
            # Handle description mapping
            if 'description' in df.columns:
                desc_series = df['description']
            elif 'summary' in df.columns:
                desc_series = df['summary']
            else:
                desc_series = self.pd.Series([''] * len(df))
            
            processed_df['description'] = desc_series.fillna('').astype(str).str.strip()
            
            # Handle strength/weight mapping - be more careful with data types
            if 'weight' in df.columns:
                strength_series = df['weight']
            elif 'strength' in df.columns:
                strength_series = df['strength']
            else:
                strength_series = self.pd.Series([1.0] * len(df))
            
            # Convert to numeric, coercing errors to 1.0
            strength_series = self.pd.to_numeric(strength_series, errors='coerce').fillna(1.0)
            processed_df['strength'] = strength_series.astype(float)
            
            processed_df['document_id'] = document_id
            
            # Handle rank - be more careful with data types
            if 'rank' in df.columns:
                rank_series = df['rank']
            else:
                rank_series = self.pd.Series([0.0] * len(df))
            
            # Convert to numeric, coercing errors to 0.0
            rank_series = self.pd.to_numeric(rank_series, errors='coerce').fillna(0.0)
            processed_df['rank'] = rank_series.astype(float)
            
            # Filter out invalid relationships
            valid_mask = (
                (processed_df['source_entity'] != '') & 
                (processed_df['target_entity'] != '') &
                (processed_df['source_entity'] != processed_df['target_entity'])
            )
            processed_df = processed_df[valid_mask]
            
            if processed_df.empty:
                logger.warning("⚠️ No valid relationships after processing")
                return None
            
            logger.info(f"✅ Processed {len(processed_df)} valid relationships")
            
            # Convert to PyArrow table
            return self.pa.Table.from_pandas(processed_df)
            
        except Exception as e:
            logger.error(f"❌ Failed to process relationships dataframe: {e}")
            logger.error(f"📋 Relationships DataFrame columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            logger.error(f"📋 Relationships DataFrame shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            return None
    
    def _process_communities_dataframe(self, df: Any, community_reports_df: Any, document_id: str) -> Any:
        """
        Process communities dataframe for LanceDB storage

        Merges communities with community_reports to get summaries and other details.
        communities.parquet has: id, community, level, parent, children, title, entity_ids, relationship_ids, text_unit_ids
        community_reports.parquet has: id, community, title, summary, full_content, rating, etc.
        """
        try:
            logger.info(f"🔄 Processing {len(df)} communities")
            logger.info(f"📋 Communities DataFrame columns: {list(df.columns)}")

            # Reset index to ensure we have clean integer indices
            df = df.reset_index(drop=True)

            processed_df = self.pd.DataFrame()

            # Map GraphRAG columns to our schema
            processed_df['community_id'] = df.get('id', df.index.astype(str)).astype(str)

            # Handle title mapping
            if 'title' in df.columns:
                title_series = df['title']
            elif 'name' in df.columns:
                title_series = df['name']
            else:
                title_series = self.pd.Series([f'Community {i}' for i in range(len(df))])

            processed_df['title'] = title_series.fillna('').astype(str).str.strip()

            # Merge with community_reports to get summaries
            # community_reports has 'community' field (numeric ID) that matches df['community']
            summary_series = self.pd.Series([''] * len(df))

            if community_reports_df is not None and not community_reports_df.empty:
                # Create a mapping from community number to summary
                if 'community' in df.columns and 'community' in community_reports_df.columns:
                    community_summary_map = {}
                    for _, report_row in community_reports_df.iterrows():
                        comm_num = report_row.get('community')
                        summary = report_row.get('summary', report_row.get('full_content', ''))
                        if comm_num is not None:
                            community_summary_map[comm_num] = str(summary)

                    # Map summaries to communities
                    summary_series = df['community'].apply(
                        lambda x: community_summary_map.get(x, '')
                    )
                    logger.info(f"📊 Merged summaries for {len([s for s in summary_series if s])} communities from community_reports")

            processed_df['summary'] = summary_series.fillna('').astype(str).str.strip()

            processed_df['document_id'] = document_id

            # Store the community number for reverse mapping (entities know their community, we need this to build member lists)
            if 'community' in df.columns:
                # Convert to int, handling NaN
                community_series = df['community'].fillna(-1)
                processed_df['community'] = self.pd.to_numeric(community_series, errors='coerce').fillna(-1).astype(int)
            else:
                processed_df['community'] = -1
            
            # Handle level - be more careful with data types
            if 'level' in df.columns:
                level_series = df['level']
            else:
                level_series = self.pd.Series([0] * len(df))
            
            # Convert to numeric, coercing errors to 0
            level_series = self.pd.to_numeric(level_series, errors='coerce').fillna(0)
            processed_df['level'] = level_series.astype(int)
            
            # Handle rating - be more careful with data types
            if 'rating' in df.columns:
                rating_series = df['rating']
            elif 'size' in df.columns:
                rating_series = df['size']
            else:
                rating_series = self.pd.Series([0.0] * len(df))
            
            # Convert to numeric, coercing errors to 0.0
            rating_series = self.pd.to_numeric(rating_series, errors='coerce').fillna(0.0)
            processed_df['rating'] = rating_series.astype(float)
            
            # Handle member entities - GraphRAG communities have entity_ids array
            if 'entity_ids' in df.columns:
                logger.info(f"📋 Found entity_ids column in communities")
                logger.info(f"📋 Sample entity_ids values (first 3): {df['entity_ids'].head(3).tolist()}")
                logger.info(f"📋 entity_ids types: {df['entity_ids'].apply(type).unique()}")

                # entity_ids is the correct field in communities.parquet
                processed_df['member_entities'] = df['entity_ids'].apply(
                    lambda x: self._extract_entities_from_relationships_safe(x)
                )

                logger.info(f"📋 Sample extracted member_entities (first 3): {processed_df['member_entities'].head(3).tolist()}")
            elif 'relationship_ids' in df.columns:
                # Fallback to relationship_ids if entity_ids not present
                processed_df['member_entities'] = df['relationship_ids'].apply(
                    lambda x: self._extract_entities_from_relationships_safe(x)
                )
            elif 'text_unit_ids' in df.columns:
                # Use text_unit_ids as a fallback
                processed_df['member_entities'] = df['text_unit_ids'].apply(
                    lambda x: self._extract_entities_from_relationships_safe(x)
                )
            else:
                # If no member tracking fields, leave empty
                processed_df['member_entities'] = '[]'

            processed_df['member_count'] = processed_df['member_entities'].apply(
                lambda x: len(json.loads(x)) if x and x != '[]' else 0
            )

            logger.info(f"📊 Community member counts: min={processed_df['member_count'].min()}, max={processed_df['member_count'].max()}, avg={processed_df['member_count'].mean():.1f}")
            
            # Filter out empty titles - but be more permissive
            processed_df = processed_df[processed_df['title'].str.len() > 0]
            
            if processed_df.empty:
                logger.warning("⚠️ No valid communities after processing")
                return None
            
            logger.info(f"✅ Processed {len(processed_df)} valid communities")
            
            # Convert to PyArrow table
            return self.pa.Table.from_pandas(processed_df)
            
        except Exception as e:
            logger.error(f"❌ Failed to process communities dataframe: {e}")
            logger.error(f"📋 Communities DataFrame columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            logger.error(f"📋 Communities DataFrame shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            return None
    
    def _extract_entities_from_relationships_safe(self, relationship_ids) -> str:
        """Safely extract entity names from relationship IDs"""
        try:
            # Debug logging - log first few calls to see what we're getting
            import random
            if random.random() < 0.1:  # Log 10% of calls to avoid spam
                logger.debug(f"🔍 Extracting entities from: {relationship_ids} (type: {type(relationship_ids)})")

            # Check for None or NaN
            if relationship_ids is None:
                return '[]'

            # For scalar values that are NaN
            if isinstance(relationship_ids, (float, int)) and self.pd.isna(relationship_ids):
                return '[]'

            # If it's already a JSON string, return it
            if isinstance(relationship_ids, str):
                if relationship_ids.startswith('['):
                    return relationship_ids
                else:
                    return f'["{relationship_ids}"]'

            # Handle list-like objects (list, numpy array, pandas array, etc.)
            # Use hasattr to check if it's iterable
            if hasattr(relationship_ids, '__iter__') and not isinstance(relationship_ids, str):
                try:
                    # Convert to list and then to JSON
                    items_list = list(relationship_ids)
                    if len(items_list) == 0:
                        return '[]'
                    return json.dumps([str(item) for item in items_list])
                except:
                    return '[]'

            # Single value - wrap in array
            return f'["{str(relationship_ids)}"]'

        except Exception as e:
            logger.debug(f"Failed to extract entities: {e}, type: {type(relationship_ids)}")
            return '[]'

    def _process_claims_dataframe(self, df: Any, document_id: str) -> Any:
        """
        Process claims dataframe for LanceDB storage

        """
        try:
            logger.info(f"🔄 Processing {len(df)} claims")

            df = df.reset_index(drop=True)
            processed_df = self.pd.DataFrame()

            # Map GraphRAG columns to our schema (direct column mapping)
            processed_df['claim_id'] = df.get('id', df.index.astype(str)).astype(str)

            # Map subject - could be 'subject_id' or 'subject'
            if 'subject_id' in df.columns:
                processed_df['subject'] = df['subject_id'].fillna('').astype(str).str.strip()
            elif 'subject' in df.columns:
                processed_df['subject'] = df['subject'].fillna('').astype(str).str.strip()
            else:
                processed_df['subject'] = ''

            # Map object - could be 'object_id' or 'object'
            if 'object_id' in df.columns:
                processed_df['object'] = df['object_id'].fillna('').astype(str).str.strip()
            elif 'object' in df.columns:
                processed_df['object'] = df['object'].fillna('').astype(str).str.strip()
            else:
                processed_df['object'] = ''

            # Map type - this is the claim type (e.g., "RESEARCH FINDINGS", "TOOL EVALUATION")
            if 'type' in df.columns:
                processed_df['type'] = df['type'].fillna('CLAIM').astype(str).str.strip()
            else:
                processed_df['type'] = 'CLAIM'

            # Map status (e.g., "TRUE", "FALSE", "SUSPECTED")
            if 'status' in df.columns:
                processed_df['status'] = df['status'].fillna('unknown').astype(str).str.strip()
            else:
                processed_df['status'] = 'unknown'

            # Map description (the main claim text)
            if 'description' in df.columns:
                processed_df['description'] = df['description'].fillna('').astype(str).str.strip()
            else:
                processed_df['description'] = ''

            # Map source_text (where the claim came from)
            if 'source_text' in df.columns:
                processed_df['source_text'] = df['source_text'].fillna('').astype(str).str.strip()
            else:
                processed_df['source_text'] = ''

            # Map dates
            if 'start_date' in df.columns:
                processed_df['start_date'] = df['start_date'].fillna('').astype(str).str.strip()
            else:
                processed_df['start_date'] = ''

            if 'end_date' in df.columns:
                processed_df['end_date'] = df['end_date'].fillna('').astype(str).str.strip()
            else:
                processed_df['end_date'] = ''

            processed_df['document_id'] = document_id

            # Filter out empty claims (at least description should exist)
            valid_mask = processed_df['description'] != ''
            processed_df = processed_df[valid_mask]

            if processed_df.empty:
                logger.warning("⚠️ No valid claims after processing")
                return None

            logger.info(f"✅ Processed {len(processed_df)} valid claims")
            logger.info(f"📊 Sample claim types: {processed_df['type'].value_counts().head(3).to_dict()}")
            return self.pa.Table.from_pandas(processed_df)

        except Exception as e:
            logger.error(f"❌ Failed to process claims dataframe: {e}")
            logger.error(f"📋 Claims DataFrame columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
            return None

    def _process_covariates_dataframe(self, df: Any, document_id: str) -> Any:
        """Process covariates dataframe for LanceDB storage"""
        try:
            logger.info(f"🔄 Processing {len(df)} covariates")

            df = df.reset_index(drop=True)
            processed_df = self.pd.DataFrame()

            # Map GraphRAG columns to our schema
            processed_df['covariate_id'] = df.get('id', df.index.astype(str)).astype(str)

            # Handle subject_id - safely check if column exists
            if 'subject_id' in df.columns:
                processed_df['subject_id'] = df['subject_id'].fillna('').astype(str).str.strip()
            else:
                processed_df['subject_id'] = ''

            # Handle subject_type - safely check if column exists
            if 'subject_type' in df.columns:
                processed_df['subject_type'] = df['subject_type'].fillna('entity').astype(str).str.strip()
            else:
                processed_df['subject_type'] = 'entity'

            # Handle covariate_type - safely check if column exists
            if 'covariate_type' in df.columns:
                processed_df['covariate_type'] = df['covariate_type'].fillna('generic').astype(str).str.strip()
            elif 'type' in df.columns:
                processed_df['covariate_type'] = df['type'].fillna('generic').astype(str).str.strip()
            else:
                processed_df['covariate_type'] = 'generic'

            # Handle text_unit_id - safely check if column exists
            if 'text_unit_id' in df.columns:
                processed_df['text_unit_id'] = df['text_unit_id'].fillna('').astype(str).str.strip()
            else:
                processed_df['text_unit_id'] = ''

            processed_df['document_id'] = document_id

            # Handle attributes - convert to JSON string
            if 'attributes' in df.columns:
                processed_df['attributes'] = df['attributes'].apply(
                    lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x) if x else '{}'
                )
            else:
                processed_df['attributes'] = '{}'

            if processed_df.empty:
                logger.warning("⚠️ No valid covariates after processing")
                return None

            logger.info(f"✅ Processed {len(processed_df)} valid covariates")
            return self.pa.Table.from_pandas(processed_df)

        except Exception as e:
            logger.error(f"❌ Failed to process covariates dataframe: {e}")
            return None

    def _process_text_units_dataframe(self, df: Any, document_id: str) -> Any:
        """Process text units dataframe for LanceDB storage with embeddings"""
        try:
            logger.info(f"🔄 Processing {len(df)} text units")

            df = df.reset_index(drop=True)
            processed_df = self.pd.DataFrame()

            # Map GraphRAG columns to our schema
            processed_df['text_unit_id'] = df.get('id', df.index.astype(str)).astype(str)

            # Handle text - safely check if column exists
            if 'text' in df.columns:
                processed_df['text'] = df['text'].fillna('').astype(str).str.strip()
            elif 'content' in df.columns:
                processed_df['text'] = df['content'].fillna('').astype(str).str.strip()
            else:
                processed_df['text'] = ''

            # Handle token count
            if 'n_tokens' in df.columns:
                n_tokens_series = self.pd.to_numeric(df['n_tokens'], errors='coerce').fillna(0)
                processed_df['n_tokens'] = n_tokens_series.astype(int)
            else:
                processed_df['n_tokens'] = 0

            processed_df['document_id'] = document_id

            # Handle chunk_id - safely check if column exists
            if 'chunk_id' in df.columns:
                processed_df['chunk_id'] = df['chunk_id'].fillna('').astype(str).str.strip()
            elif 'chunk' in df.columns:
                processed_df['chunk_id'] = df['chunk'].fillna('').astype(str).str.strip()
            else:
                processed_df['chunk_id'] = ''

            # Handle text_embedding - convert to list format for LanceDB
            if 'text_embedding' in df.columns:
                def safe_convert_embedding(emb):
                    if emb is None or (isinstance(emb, float) and self.pd.isna(emb)):
                        return [0.0] * 768
                    elif isinstance(emb, list):
                        return emb[:768] if len(emb) >= 768 else emb + [0.0] * (768 - len(emb))
                    elif isinstance(emb, str):
                        try:
                            parsed = json.loads(emb)
                            return parsed[:768] if len(parsed) >= 768 else parsed + [0.0] * (768 - len(parsed))
                        except:
                            return [0.0] * 768
                    else:
                        return [0.0] * 768

                processed_df['text_embedding'] = df['text_embedding'].apply(safe_convert_embedding)
                logger.info("✅ Text unit embeddings found and processed")
            else:
                logger.warning("⚠️ No text_embedding column found in text_units - using zero vectors. Vector search will not work properly!")
                logger.warning("⚠️ To enable vector search, ensure GraphRAG is configured to generate embeddings")
                processed_df['text_embedding'] = [[0.0] * 768] * len(processed_df)

            # Handle entity_ids - REQUIRED for GraphRAG local/drift search
            def safe_convert_ids_to_json(ids):
                """Convert entity/relationship IDs to JSON string

                Handles multiple input types:
                - None/NaN: Returns empty array '[]'
                - String: Returns as-is if JSON, wraps in array if single value
                - List: Converts to JSON string
                - Numpy array: Converts to list then JSON
                - PyArrow array: Converts to list then JSON
                """
                import numpy as np

                # Handle None/NaN
                if ids is None or (isinstance(ids, float) and self.pd.isna(ids)):
                    return '[]'

                # Handle strings
                elif isinstance(ids, str):
                    # Already a JSON string
                    if ids.startswith('['):
                        return ids
                    # Single ID as string
                    return f'["{ids}"]'

                # Handle regular Python lists
                elif isinstance(ids, list):
                    return json.dumps(ids)

                # Handle numpy arrays (from parquet files)
                elif isinstance(ids, np.ndarray):
                    return json.dumps(ids.tolist())

                # Handle pyarrow arrays (from parquet files)
                elif hasattr(ids, 'to_pylist'):  # PyArrow arrays have to_pylist() method
                    return json.dumps(ids.to_pylist())

                # Handle any other iterable (tuple, set, etc.)
                elif hasattr(ids, '__iter__') and not isinstance(ids, (str, bytes)):
                    try:
                        return json.dumps(list(ids))
                    except (TypeError, ValueError):
                        return '[]'

                # Fallback for unknown types
                else:
                    logger.warning(f"⚠️ Unknown type for IDs: {type(ids)}, returning empty array")
                    return '[]'

            if 'entity_ids' in df.columns:
                # Debug: Check the first entity_ids value type
                if len(df) > 0:
                    first_entity_ids = df['entity_ids'].iloc[0]
                    logger.info(f"🔍 First entity_ids type: {type(first_entity_ids).__name__}")
                    logger.info(f"🔍 First entity_ids value preview: {str(first_entity_ids)[:200]}")

                processed_df['entity_ids'] = df['entity_ids'].apply(safe_convert_ids_to_json)

                # Debug: Verify conversion
                if len(processed_df) > 0:
                    first_converted = processed_df['entity_ids'].iloc[0]
                    logger.info(f"✅ Entity IDs converted - First value: {first_converted[:200]}")
                logger.info("✅ Entity IDs found and processed")
            else:
                logger.warning("⚠️ No entity_ids column found in text_units - local search will be limited")
                processed_df['entity_ids'] = '[]'

            # Handle relationship_ids - REQUIRED for GraphRAG local/drift search
            if 'relationship_ids' in df.columns:
                # Debug: Check the first relationship_ids value type
                if len(df) > 0:
                    first_rel_ids = df['relationship_ids'].iloc[0]
                    logger.info(f"🔍 First relationship_ids type: {type(first_rel_ids).__name__}")
                    logger.info(f"🔍 First relationship_ids value preview: {str(first_rel_ids)[:200]}")

                processed_df['relationship_ids'] = df['relationship_ids'].apply(safe_convert_ids_to_json)

                # Debug: Verify conversion
                if len(processed_df) > 0:
                    first_converted = processed_df['relationship_ids'].iloc[0]
                    logger.info(f"✅ Relationship IDs converted - First value: {first_converted[:200]}")
                logger.info("✅ Relationship IDs found and processed")
            else:
                logger.warning("⚠️ No relationship_ids column found in text_units - local search will be limited")
                processed_df['relationship_ids'] = '[]'

            # Filter out empty text units
            processed_df = processed_df[processed_df['text'] != '']

            if processed_df.empty:
                logger.warning("⚠️ No valid text units after processing")
                return None

            logger.info(f"✅ Processed {len(processed_df)} valid text units")
            return self.pa.Table.from_pandas(processed_df)

        except Exception as e:
            logger.error(f"❌ Failed to process text units dataframe: {e}")
            return None
    
    # SEARCH AND QUERY METHODS
    def search_entities(self, query: str, bucket: str = None, limit: int = 50) -> List[Dict]:
        """Search entities by query with JOIN to documents"""
        try:
            entities_df = self.tables["entities"].to_pandas()
            docs_df = self.tables["documents"].to_pandas()
            
            if entities_df.empty or docs_df.empty:
                return []
            
            # JOIN entities with documents
            joined_df = entities_df.merge(docs_df, on='document_id', how='inner')
            
            # Filter by query terms
            query_lower = query.lower()
            mask = (
                joined_df['name'].str.lower().str.contains(query_lower, na=False) |
                joined_df['description'].str.lower().str.contains(query_lower, na=False)
            )
            
            # Filter by bucket if specified
            if bucket:
                mask = mask & (joined_df['bucket'] == bucket)
            
            filtered_df = joined_df[mask].head(limit)
            
            results = []
            for _, row in filtered_df.iterrows():
                entity_data = {
                    "entity_id": row['entity_id'],
                    "name": row['name'],
                    "entity_type": row['type'],
                    "description": row['description'],
                    "document_id": row['document_id'],
                    "bucket": row['bucket'],
                    "degree": row['degree'],
                    "rank": row['rank'],
                    "document_source": row['source_url'] if row['bucket'] == 'news' else row['filename']
                }
                results.append(entity_data)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Entity search failed: {e}")
            return []
    
    def search_relationships(self, query: str, bucket: str = None, limit: int = 50) -> List[Dict]:
        """Search relationships by query with JOIN to documents"""
        try:
            relationships_df = self.tables["relationships"].to_pandas()
            docs_df = self.tables["documents"].to_pandas()
            
            if relationships_df.empty or docs_df.empty:
                return []
            
            # JOIN relationships with documents
            joined_df = relationships_df.merge(docs_df, on='document_id', how='inner')
            
            # Filter by query terms
            query_lower = query.lower()
            mask = (
                joined_df['source_entity'].str.lower().str.contains(query_lower, na=False) |
                joined_df['target_entity'].str.lower().str.contains(query_lower, na=False) |
                joined_df['description'].str.lower().str.contains(query_lower, na=False)
            )
            
            # Filter by bucket if specified
            if bucket:
                mask = mask & (joined_df['bucket'] == bucket)
            
            filtered_df = joined_df[mask].head(limit)
            
            results = []
            for _, row in filtered_df.iterrows():
                rel_data = {
                    "relationship_id": row['relationship_id'],
                    "source_entity": row['source_entity'],
                    "target_entity": row['target_entity'],
                    "relationship_type": "RELATED",
                    "description": row['description'],
                    "strength": row['strength'],
                    "document_id": row['document_id'],
                    "bucket": row['bucket'],
                    "rank": row['rank'],
                    "document_source": row['source_url'] if row['bucket'] == 'news' else row['filename']
                }
                results.append(rel_data)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Relationship search failed: {e}")
            return []
    
    def get_document_graph_data(self, filename: str, bucket: str = None, 
                               max_nodes: int = 100, max_edges: int = 200, 
                               include_communities: bool = True) -> Dict[str, Any]:
        """Get complete graph data for a document by filename"""
        try:
            docs_df = self.tables["documents"].to_pandas()
            
            if docs_df.empty:
                return None
            
            # Filter by filename and bucket
            mask = docs_df['filename'] == filename
            if bucket:
                mask = mask & (docs_df['bucket'] == bucket)
            
            doc_matches = docs_df[mask]
            if doc_matches.empty:
                return None
            
            doc_record = doc_matches.iloc[0]
            document_id = doc_record['document_id']
            
            return self._get_graph_data_by_document_id(document_id, doc_record, max_nodes, max_edges, include_communities)
            
        except Exception as e:
            logger.error(f"❌ Failed to get document graph data: {e}")
            return None
    
    def get_document_graph_data_by_source_url(self, source_url: str, bucket: str = None, 
                                            max_nodes: int = 100, max_edges: int = 200, 
                                            include_communities: bool = True) -> Dict[str, Any]:
        """Get complete graph data for a document by source_url"""
        try:
            docs_df = self.tables["documents"].to_pandas()
            
            if docs_df.empty:
                return None
            
            # Filter by source_url and bucket
            mask = docs_df['source_url'] == source_url
            if bucket:
                mask = mask & (docs_df['bucket'] == bucket)
            
            doc_matches = docs_df[mask]
            if doc_matches.empty:
                return None
            
            doc_record = doc_matches.iloc[0]
            document_id = doc_record['document_id']
            
            return self._get_graph_data_by_document_id(document_id, doc_record, max_nodes, max_edges, include_communities)
            
        except Exception as e:
            logger.error(f"❌ Failed to get document graph data by source URL: {e}")
            return None
    
    def _get_graph_data_by_document_id(self, document_id: str, doc_record, max_nodes: int, 
                                     max_edges: int, include_communities: bool) -> Dict[str, Any]:
        """
        Helper method to get graph data by document ID
        
        """
        try:
            # First, get relationships to determine which entities to include
            relationships_df = self.tables["relationships"].to_pandas()
            relationships_mask = relationships_df['document_id'] == document_id
            relationships_filtered = relationships_df[relationships_mask].head(max_edges)
            
            # Build set of entity names that appear in relationships
            connected_entity_names: Set[str] = set()
            relationships = []
            
            for _, row in relationships_filtered.iterrows():
                source_entity = str(row['source_entity']).strip()
                target_entity = str(row['target_entity']).strip()
                
                # Add both source and target to the set of connected entities
                connected_entity_names.add(source_entity)
                connected_entity_names.add(target_entity)
                
                relationships.append({
                    "relationship_id": row['relationship_id'],
                    "source_entity": source_entity,
                    "target_entity": target_entity,
                    "description": row['description'],
                    "strength": row['strength'],
                    "rank": row['rank']
                })
            
            logger.info(f"🔍 Found {len(connected_entity_names)} unique connected entities from {len(relationships)} relationships")
            
            # Now get entities, but only those that appear in relationships
            entities_df = self.tables["entities"].to_pandas()
            entities_mask = entities_df['document_id'] == document_id
            entities_filtered = entities_df[entities_mask]
            
            # Filter entities to only include those with relationships
            # Normalize entity names for comparison (case-insensitive, strip whitespace)
            entities_filtered['name_normalized'] = entities_filtered['name'].str.strip().str.lower()
            connected_entity_names_normalized = {name.lower().strip() for name in connected_entity_names}
            
            entities_with_relationships = entities_filtered[
                entities_filtered['name_normalized'].isin(connected_entity_names_normalized)
            ]
            
            # Apply max_nodes limit after filtering
            entities_with_relationships = entities_with_relationships.head(max_nodes)
            
            entities = []
            for _, row in entities_with_relationships.iterrows():
                entities.append({
                    "entity_id": row['entity_id'],
                    "name": str(row['name']).strip(),  # Use original case
                    "type": row['type'],
                    "description": row['description'],
                    "degree": row['degree'],
                    "rank": row['rank']
                })
            
            logger.info(f"✅ Filtered to {len(entities)} entities that have relationships (from {len(entities_filtered)} total entities)")
            
            # Get communities
            communities = []
            if include_communities:
                communities_df = self.tables["communities"].to_pandas()
                communities_mask = communities_df['document_id'] == document_id
                communities_filtered = communities_df[communities_mask]
                
                for _, row in communities_filtered.iterrows():
                    try:
                        member_entities = json.loads(row['member_entities'])
                    except:
                        member_entities = []
                    
                    communities.append({
                        "community_id": row['community_id'],
                        "title": row['title'],
                        "summary": row['summary'],
                        "member_entities": member_entities,
                        "member_count": row['member_count'],
                        "rating": row['rating'],
                        "level": row['level']
                    })
            
            # Convert timestamp to string safely
            processing_timestamp = doc_record['processing_timestamp']
            if hasattr(processing_timestamp, 'isoformat'):
                timestamp_str = processing_timestamp.isoformat()
            else:
                timestamp_str = str(processing_timestamp)
            
            return {
                "metadata": {
                    "document_id": document_id,
                    "filename": doc_record['filename'],
                    "source_identifier": doc_record['source_url'] if doc_record['bucket'] == 'news' else doc_record['filename'],
                    "bucket": doc_record['bucket'],
                    "processing_timestamp": timestamp_str,
                    "processing_duration": 0,
                    "entities_count": len(entities),
                    "relationships_count": len(relationships),
                    "communities_count": len(communities),
                    "total_entities_in_db": int(doc_record['entities_count']),
                    "connected_entities_returned": len(entities)
                },
                "entities": entities,
                "relationships": relationships,
                "communities": communities
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get graph data by document ID: {e}")
            return None
    
    def get_available_documents(self, bucket: str = None) -> List[str]:
        """Get list of available documents"""
        try:
            docs_df = self.tables["documents"].to_pandas()
            
            if docs_df.empty:
                return []
            
            if bucket:
                docs_df = docs_df[docs_df['bucket'] == bucket]
            
            # Return source_url for news, filename for others
            result = []
            for _, row in docs_df.iterrows():
                if row['bucket'] == 'news':
                    result.append(row['source_url'])
                else:
                    result.append(row['filename'])
            
            return list(set(result))
            
        except Exception as e:
            logger.error(f"❌ Failed to get available documents: {e}")
            return []
    
    def get_document_stats(self, bucket: str = None) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            docs_df = self.tables["documents"].to_pandas()
            
            if docs_df.empty:
                return {
                    "total_documents": 0,
                    "total_entities": 0,
                    "total_relationships": 0,
                    "total_communities": 0,
                    "recent_documents": []
                }
            
            if bucket:
                docs_df = docs_df[docs_df['bucket'] == bucket]
            
            total_entities = docs_df['entities_count'].sum()
            total_relationships = docs_df['relationships_count'].sum()
            total_communities = docs_df['communities_count'].sum()
            
            # Get recent documents
            recent_docs_df = docs_df.tail(5)
            recent_documents = []
            for _, row in recent_docs_df.iterrows():
                if row['bucket'] == 'news':
                    recent_documents.append(row['source_url'])
                else:
                    recent_documents.append(row['filename'])
            
            return {
                "total_documents": len(docs_df),
                "total_entities": int(total_entities),
                "total_relationships": int(total_relationships),
                "total_communities": int(total_communities),
                "avg_processing_time": 0,
                "recent_documents": recent_documents
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                "total_documents": 0,
                "total_entities": 0,
                "total_relationships": 0,
                "total_communities": 0,
                "recent_documents": []
            }