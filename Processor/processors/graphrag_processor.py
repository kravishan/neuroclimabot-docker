"""
GraphRAG Processor - Enhanced with automatic LanceDB data transfer
"""

import logging
import asyncio
import subprocess
import json
import shutil
import os
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

from config import config
from storage.master_graphrag import MasterGraphRAGAccumulator

logger = logging.getLogger(__name__)


class GraphRAGProcessor:
    """GraphRAG processor with master output accumulation"""

    def __init__(self):
        self.base_dir = Path("./workspaces")
        self.base_dir.mkdir(exist_ok=True)
        self.master_accumulator = MasterGraphRAGAccumulator()  # Master output manager
        self.root_prompts = Path("./graphrag/prompts")

        # Single settings file for all buckets (SIMPLIFIED)
        self.settings_file = Path("./graphrag/settings.yaml")

        self._validate_setup()
    
    def _validate_setup(self):
        """Validate settings file and prompts exist"""
        # Check settings file
        if not self.settings_file.exists():
            logger.error(f"❌ Settings file not found: {self.settings_file}")
            raise FileNotFoundError(f"GraphRAG settings file required: {self.settings_file}")

        # Check prompts directory
        if not self.root_prompts.exists():
            logger.error(f"❌ Prompts directory not found: {self.root_prompts}")
            raise FileNotFoundError(f"Prompts directory required: {self.root_prompts}")

        logger.info(f"✅ GraphRAG processor initialized")
        logger.info(f"   Settings: {self.settings_file}")
        logger.info(f"   Prompts: {self.root_prompts}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for workspace directory"""
        if filename.startswith(('http://', 'https://')):
            return self._sanitize_url(filename)

        # Basic sanitization - preserve spaces, only replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*#&=%]', '_', filename)
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized[:100] if len(sanitized) > 100 else sanitized
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for workspace directory name"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = unquote(parsed.path.strip('/'))

            if path:
                meaningful_part = path.split('/')[-1]
                meaningful_part = re.sub(r'[^a-zA-Z0-9\-_]', '_', meaningful_part)
                sanitized = f"{domain}_{meaningful_part}"
            else:
                sanitized = domain

            sanitized = re.sub(r'_+', '_', sanitized).strip('_')
            return sanitized[:120] if len(sanitized) > 120 else sanitized

        except Exception:
            return re.sub(r'[^a-zA-Z0-9\-_]', '_', url)[:120]

    def _url_to_safe_filename(self, url: str) -> str:
        """Convert URL to filesystem-safe filename while preserving the full URL"""
        # Replace only characters that are problematic for filesystems
        # Keep the URL structure intact as much as possible
        safe_url = url.replace('://', '_')  # Replace :// with _
        safe_url = safe_url.replace('/', '_')  # Replace / with _
        safe_url = safe_url.replace('?', '_')  # Replace ? with _
        safe_url = safe_url.replace('&', '_')  # Replace & with _
        safe_url = safe_url.replace('=', '_')  # Replace = with _
        safe_url = safe_url.replace('#', '_')  # Replace # with _
        safe_url = safe_url.replace('%', '_')  # Replace % with _
        safe_url = safe_url.replace('<', '_')  # Replace < with _
        safe_url = safe_url.replace('>', '_')  # Replace > with _
        safe_url = safe_url.replace(':', '_')  # Replace : with _
        safe_url = safe_url.replace('"', '_')  # Replace " with _
        safe_url = safe_url.replace('|', '_')  # Replace | with _
        safe_url = safe_url.replace('*', '_')  # Replace * with _
        safe_url = safe_url.replace('\\', '_')  # Replace \ with _

        # Collapse multiple underscores to single
        safe_url = re.sub(r'_+', '_', safe_url)
        safe_url = safe_url.strip('_')

        # Limit length to avoid filesystem issues (keep first 250 chars)
        if len(safe_url) > 250:
            safe_url = safe_url[:250]

        return safe_url
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract readable title from URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            if path:
                last_part = path.split('/')[-1]
                title = unquote(last_part).replace('-', ' ').replace('_', ' ')
                title = re.sub(r'\.(html|htm|php)$', '', title, flags=re.IGNORECASE)
                title = ' '.join(word.capitalize() for word in title.split() if word)
                
                if title and len(title.strip()) > 3:
                    return title[:150]
            
            domain = parsed.netloc.replace('www.', '')
            return f"Article from {domain.split('.')[0].title()}"
            
        except Exception:
            return "Document"
    
    def _validate_url(self, url: str) -> bool:
        """Check if string is a valid URL"""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return False
        
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme)
        except Exception:
            return False
    
    def _generate_unique_identifier(self, filename: str, bucket: str) -> str:
        """Generate unique identifier for documents without URLs"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = re.sub(r'[^a-zA-Z0-9\-_]', '_', filename)
        return f"{bucket}://{safe_filename}_{timestamp}_{uuid.uuid4().hex[:8]}"

    async def process_document_graphrag(self, text_content: str, filename: str, bucket: str,
                                      source_url: str = "") -> Dict[str, Any]:
        """Process document using GraphRAG CLI workflow with automatic LanceDB transfer"""
        start_time = datetime.now()

        try:
            # Use single settings file for all buckets
            settings_file = self.settings_file
            
            # Determine document info
            final_source_url = source_url.strip() if source_url else ""
            
            if self._validate_url(final_source_url):
                document_identifier = final_source_url
                document_title = self._extract_title_from_url(final_source_url)
                is_url_document = True
            elif self._validate_url(filename):
                final_source_url = filename
                document_identifier = filename
                document_title = self._extract_title_from_url(filename)
                is_url_document = True
            else:
                document_identifier = filename
                document_title = filename
                is_url_document = False
                if not final_source_url:
                    final_source_url = self._generate_unique_identifier(filename, bucket)
            
            # Create workspace
            sanitized_identifier = self._sanitize_filename(document_identifier)
            workspace_id = f"{bucket}_{sanitized_identifier}_{uuid.uuid4().hex[:8]}"
            workspace_path = self.base_dir / workspace_id
            
            logger.info(f"🚀 Processing {document_title} ({len(text_content)} chars)")
            
            # Setup workspace (settings file is now class attribute)
            await self._setup_workspace(workspace_path, text_content, document_identifier, bucket)
            
            # Run GraphRAG indexing
            success = await self._run_graphrag_indexing(workspace_path)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if success:
                logger.info(f"✅ GraphRAG indexing completed in {processing_time:.2f}s")

                # Merge workspace data to master GraphRAG output
                logger.info(f"📊 Merging to master GraphRAG output...")
                merge_result = self.master_accumulator.merge_workspace_to_master(workspace_path)

                if merge_result["status"] == "success":
                    logger.info(f"✅ Merged to master: +{merge_result.get('entities_added', 0)}E, "
                              f"+{merge_result.get('relationships_added', 0)}R, "
                              f"+{merge_result.get('communities_added', 0)}C")

                    # Get counts from merge result
                    entities_count = merge_result.get('entities_added', 0)
                    relationships_count = merge_result.get('relationships_added', 0)
                    communities_count = merge_result.get('communities_added', 0)

                    # Optional: Cleanup workspace after successful merge
                    if config.get('graphrag.cleanup_temp', True):
                        await self._cleanup_workspace_async(workspace_path)
                        logger.info(f"🧹 Workspace cleaned up: {workspace_path}")

                    return {
                        "status": "success",
                        "document_id": str(uuid.uuid4()),  # Generate document ID
                        "document_title": document_title,
                        "source_url": final_source_url,
                        "filename": filename,
                        "is_url_document": is_url_document,
                        "entities_count": entities_count,
                        "relationships_count": relationships_count,
                        "communities_count": communities_count,
                        "processing_time": processing_time,
                        "bucket": bucket,
                        "workspace_path": str(workspace_path)
                    }
                else:
                    logger.warning(f"⚠️  Master merge had issues: {merge_result.get('status')}")
                    return {
                        "status": "partial_success",
                        "message": f"GraphRAG completed but master merge had issues: {merge_result.get('message')}",
                        "processing_time": processing_time,
                        "bucket": bucket,
                        "workspace_path": str(workspace_path)
                    }
                    
            else:
                logger.error(f"❌ GraphRAG indexing failed in {processing_time:.2f}s")
                return {
                    "status": "failed",
                    "message": "GraphRAG indexing failed",
                    "processing_time": processing_time,
                    "bucket": bucket,
                    "workspace_path": str(workspace_path)
                }
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"💥 GraphRAG exception: {e}")
            return {
                "status": "failed",
                "message": f"GraphRAG processing failed: {str(e)}",
                "processing_time": processing_time,
                "bucket": bucket
            }

    def _find_artifacts_directory(self, output_dir: Path) -> Path:
        """Find directory containing GraphRAG parquet files (NEW: direct output structure)"""
        if not output_dir.exists():
            logger.error(f"❌ Output directory doesn't exist: {output_dir}")
            return None
        
        # Check if parquet files are directly in output directory
        expected_files = [
            "entities.parquet",
            "relationships.parquet", 
            "communities.parquet"
        ]
        
        # Check if files exist directly in output directory
        files_in_output = [f for f in expected_files if (output_dir / f).exists()]
        
        if len(files_in_output) >= 2:  # At least entities and relationships
            logger.info(f"📂 Found parquet files directly in output directory: {files_in_output}")
            return output_dir
        
        # Fallback: Check for old artifacts subdirectory structure
        artifacts_dirs = list(output_dir.glob("**/artifacts"))
        if artifacts_dirs:
            artifacts_dir = artifacts_dirs[0]
            logger.info(f"📂 Found artifacts subdirectory: {artifacts_dir}")
            return artifacts_dir
        
        # Fallback: Check timestamped directories
        timestamped_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        if timestamped_dirs:
            latest_dir = max(timestamped_dirs, key=lambda x: x.stat().st_mtime)
            if any((latest_dir / f).exists() for f in expected_files):
                logger.info(f"📂 Found parquet files in timestamped directory: {latest_dir}")
                return latest_dir
        
        # Debug: List what's actually in the output directory
        contents = []
        try:
            for item in output_dir.iterdir():
                if item.is_file():
                    contents.append(f"FILE: {item.name}")
                elif item.is_dir():
                    contents.append(f"DIR: {item.name}")
        except:
            pass
        
        logger.error(f"❌ No GraphRAG parquet files found in {output_dir}")
        logger.error(f"📋 Directory contents: {contents}")
        return None
    
    async def _setup_workspace(self, workspace_path: Path, text_content: str,
                              document_identifier: str, bucket: str):
        """Setup GraphRAG workspace"""
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Copy settings (using single settings file for all buckets)
        shutil.copy2(self.settings_file, workspace_path / "settings.yaml")
        logger.info(f"✅ Copied settings.yaml to workspace")

        # Copy .env file if exists (use absolute path to find it reliably)
        # Try multiple locations: current dir, parent dir, and script's parent dir
        possible_env_locations = [
            Path(".env"),  # Current working directory
            Path(__file__).parent.parent / ".env",  # Processor directory
            Path.cwd() / ".env"  # Explicitly current working directory
        ]

        root_env = None
        for env_path in possible_env_locations:
            if env_path.exists():
                root_env = env_path
                break

        if root_env:
            shutil.copy2(root_env, workspace_path / ".env")
            logger.info(f"✅ Copied .env from {root_env.absolute()} to workspace")
        else:
            logger.error(f"❌ No .env file found in any expected location!")
            logger.error(f"   Tried: {[str(p.absolute()) for p in possible_env_locations]}")
            logger.error(f"   GraphRAG will fail without environment variables!")

        # Copy prompts
        workspace_prompts_dir = workspace_path / "prompts"
        if workspace_prompts_dir.exists():
            shutil.rmtree(workspace_prompts_dir)
        shutil.copytree(self.root_prompts, workspace_prompts_dir)
        
        # Create input file
        input_dir = workspace_path / "input"
        input_dir.mkdir(exist_ok=True)

        # Generate safe filename - preserve full URL for document name
        if document_identifier.startswith(('http://', 'https://')):
            # Use full URL as filename (filesystem-safe version)
            sanitized_name = self._url_to_safe_filename(document_identifier)
        else:
            sanitized_name = self._sanitize_filename(document_identifier)

        txt_filename = f"{sanitized_name}.txt"
        if len(txt_filename) > 255:  # Filesystem limit
            txt_filename = f"{sanitized_name[:250]}.txt"

        input_file = input_dir / txt_filename

        try:
            with open(input_file, 'w', encoding='utf-8', errors='replace') as f:
                f.write(text_content)
            logger.info(f"✅ Created input file: {txt_filename}")
        except Exception as e:
            # Fallback filename
            logger.warning(f"⚠️ Failed to create file with name {txt_filename}: {e}")
            fallback_filename = f"document_{uuid.uuid4().hex[:8]}.txt"
            input_file = input_dir / fallback_filename
            with open(input_file, 'w', encoding='utf-8', errors='replace') as f:
                f.write(text_content)
            logger.info(f"✅ Created input file with fallback name: {fallback_filename}")
    
    async def _run_graphrag_indexing(self, workspace_path: Path) -> bool:
        """Run GraphRAG indexing with full logging"""
        try:
            # Load environment variables from workspace .env file before running
            workspace_env_file = workspace_path / ".env"
            if workspace_env_file.exists():
                load_dotenv(workspace_env_file, override=True)
                logger.info(f"✅ Loaded environment variables from {workspace_env_file}")
            else:
                logger.warning(f"⚠️  Workspace .env file not found at {workspace_env_file}")

            # Convert to absolute path for GraphRAG --root parameter
            absolute_workspace = workspace_path.resolve()
            logger.info(f"📂 Running GraphRAG with workspace: {absolute_workspace}")

            result = await self._run_command([
                "graphrag", "index",
                "--root", str(absolute_workspace),
                "--method", "standard",
                "--logger", "rich"
            ], workspace_path)

            # Log the full output regardless of success/failure
            if result.stdout:
                logger.info(f"📋 GraphRAG STDOUT:\n{result.stdout}")

            if result.stderr:
                logger.error(f"📋 GraphRAG STDERR:\n{result.stderr}")

            if result.returncode == 0:
                logger.info("✅ GraphRAG indexing completed successfully")
                return True
            else:
                logger.error(f"❌ GraphRAG failed with return code: {result.returncode}")
                return False

        except Exception as e:
            logger.error(f"💥 GraphRAG indexing exception: {e}")
            return False
    
    async def _run_command(self, cmd: List[str], workspace_path: Path = None) -> subprocess.CompletedProcess:
        """Run command asynchronously with workspace environment"""
        loop = asyncio.get_event_loop()

        def run_sync():
            env = os.environ.copy()
            # Force UTF-8 encoding for all Python operations
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            # Windows-specific: Force UTF-8 for console output
            env['PYTHONLEGACYWINDOWSSTDIO'] = '0'

            # Load workspace .env file into environment if provided
            if workspace_path:
                workspace_env = workspace_path / ".env"
                if workspace_env.exists():
                    # Parse .env file manually and add to environment
                    with open(workspace_env, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                env[key.strip()] = value.strip()
                    logger.info(f"✅ Loaded {len([l for l in open(workspace_env, encoding='utf-8').readlines() if '=' in l and not l.startswith('#')])} env vars from workspace")

            # GraphRAG handles its own working directory via --root parameter
            # Don't set cwd here to avoid path resolution issues

            try:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=18000, # Updated to 5 hours
                    env=env,
                    encoding='utf-8',
                    errors='replace'
                )
            except UnicodeDecodeError as e:
                # Fallback: Run with errors='ignore' if UTF-8 fails
                logger.warning(f"⚠️  UTF-8 decode failed, retrying with errors='ignore': {e}")
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=18000, # Updated to 5 hours
                    env=env,
                    encoding='utf-8',
                    errors='ignore'
                )

        return await loop.run_in_executor(None, run_sync)
    
    async def _cleanup_workspace_async(self, workspace_path: Path):
        """Async workspace cleanup"""
        loop = asyncio.get_event_loop()
        
        def cleanup_sync():
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
        
        await loop.run_in_executor(None, cleanup_sync)
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces"""
        workspaces = []
        
        if not self.base_dir.exists():
            return workspaces
        
        for workspace_dir in self.base_dir.iterdir():
            if workspace_dir.is_dir():
                try:
                    output_dir = workspace_dir / "output"
                    has_output = output_dir.exists() and any(output_dir.iterdir())
                    
                    bucket = workspace_dir.name.split('_')[0] if '_' in workspace_dir.name else 'unknown'
                    
                    # Determine status
                    status = "processing"
                    if has_output:
                        artifacts_dir = self._find_artifacts_directory(output_dir)
                        if artifacts_dir:
                            expected_files = ["create_final_entities.parquet", "create_final_relationships.parquet"]
                            found_files = [f for f in expected_files if (artifacts_dir / f).exists()]
                            status = "completed" if len(found_files) >= 2 else "partial"
                        else:
                            status = "failed"
                    
                    workspaces.append({
                        "workspace_id": workspace_dir.name,
                        "bucket": bucket,
                        "status": status,
                        "created_time": datetime.fromtimestamp(workspace_dir.stat().st_ctime).isoformat()
                    })
                    
                except Exception:
                    continue
        
        return sorted(workspaces, key=lambda x: x["created_time"], reverse=True)
    
    async def cleanup_workspace_by_id(self, workspace_id: str) -> Dict[str, Any]:
        """Cleanup specific workspace"""
        workspace_path = self.base_dir / workspace_id
        
        if not workspace_path.exists():
            return {"status": "error", "message": f"Workspace {workspace_id} not found"}
        
        try:
            await self._cleanup_workspace_async(workspace_path)
            return {"status": "success", "message": f"Workspace {workspace_id} cleaned up"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to cleanup: {str(e)}"}


# Global processor instance
graphrag_processor = GraphRAGProcessor()