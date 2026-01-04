"""
Scientific Data Extractor

Specialized extractor for scientific data files (CSV, Excel, NetCDF, HDF5, etc.)

"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ScientificDataExtractor:
    """Extract and process scientific data files for RAG."""

    def __init__(self):
        self.enabled = os.getenv("ENABLE_SCIENTIFIC_DATA_PROCESSING", "True").lower() == "true"
        self.supported_formats = os.getenv(
            "SCIENTIFIC_DATA_FORMATS",
            "csv,tsv,xlsx,xls,nc,netcdf,hdf5,h5,mat,parquet"
        ).split(",")

        # Configuration
        self.csv_sample_rows = int(os.getenv("CSV_SAMPLE_ROWS", "100"))
        self.csv_include_stats = os.getenv("CSV_INCLUDE_STATISTICS", "True").lower() == "true"
        self.excel_all_sheets = os.getenv("EXCEL_PROCESS_ALL_SHEETS", "True").lower() == "true"
        self.netcdf_extract_metadata = os.getenv("NETCDF_EXTRACT_METADATA", "True").lower() == "true"
        self.netcdf_sample_arrays = os.getenv("NETCDF_SAMPLE_ARRAYS", "True").lower() == "true"
        self.netcdf_max_sample = int(os.getenv("NETCDF_MAX_ARRAY_SAMPLE", "1000"))

        logger.info(f"📊 Scientific Data Extractor initialized - Formats: {self.supported_formats}")

    def is_scientific_data_file(self, filename: str) -> bool:
        """Check if file is a scientific data format."""
        ext = Path(filename).suffix.lower().lstrip(".")
        return ext in self.supported_formats

    async def extract_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Extract data from CSV/TSV files.

        Returns structured data with schema, statistics, and samples.
        """
        import pandas as pd

        try:
            # Detect delimiter
            with open(file_path, 'r') as f:
                first_line = f.readline()
                delimiter = '\t' if '\t' in first_line else ','

            # Read CSV
            df = pd.read_csv(file_path, delimiter=delimiter)

            # Extract metadata
            metadata = {
                "format": "CSV/TSV",
                "filename": Path(file_path).name,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }

            # Generate statistics for numeric columns
            statistics = {}
            if self.csv_include_stats:
                numeric_cols = df.select_dtypes(include=['number']).columns
                for col in numeric_cols:
                    statistics[col] = {
                        "mean": float(df[col].mean()),
                        "std": float(df[col].std()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "median": float(df[col].median()),
                        "count": int(df[col].count()),
                        "missing": int(df[col].isna().sum())
                    }

            # Sample data
            sample_data = df.head(self.csv_sample_rows).to_dict(orient='records')

            # Generate semantic description
            description = self._generate_csv_description(df, metadata, statistics)

            return {
                "metadata": metadata,
                "statistics": statistics,
                "sample_data": sample_data,
                "description": description,
                "text_for_embedding": description
            }

        except Exception as e:
            logger.error(f"Error extracting CSV: {e}")
            raise

    async def extract_excel(self, file_path: str) -> Dict[str, Any]:
        """Extract data from Excel files (.xlsx, .xls)."""
        import pandas as pd

        try:
            excel_file = pd.ExcelFile(file_path)
            sheets_data = []

            sheet_names = excel_file.sheet_names
            if not self.excel_all_sheets:
                sheet_names = [sheet_names[0]]  # Only first sheet

            for sheet_name in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

                sheet_info = {
                    "sheet_name": sheet_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "sample_data": df.head(self.csv_sample_rows).to_dict(orient='records')
                }

                # Statistics
                if self.csv_include_stats:
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    sheet_info["statistics"] = {}
                    for col in numeric_cols:
                        sheet_info["statistics"][col] = {
                            "mean": float(df[col].mean()),
                            "std": float(df[col].std()),
                            "min": float(df[col].min()),
                            "max": float(df[col].max())
                        }

                sheets_data.append(sheet_info)

            # Generate description
            description = self._generate_excel_description(sheets_data)

            return {
                "metadata": {
                    "format": "Excel",
                    "filename": Path(file_path).name,
                    "total_sheets": len(excel_file.sheet_names),
                    "sheet_names": excel_file.sheet_names
                },
                "sheets": sheets_data,
                "description": description,
                "text_for_embedding": description
            }

        except Exception as e:
            logger.error(f"Error extracting Excel: {e}")
            raise

    async def extract_netcdf(self, file_path: str) -> Dict[str, Any]:
        """Extract data from NetCDF files."""
        try:
            import xarray as xr

            # Open dataset
            ds = xr.open_dataset(file_path)

            # Extract metadata
            metadata = {
                "format": "NetCDF",
                "filename": Path(file_path).name,
                "dimensions": {name: int(size) for name, size in ds.dims.items()},
                "coordinates": list(ds.coords.keys()),
                "variables": list(ds.data_vars.keys())
            }

            # Extract global attributes
            if self.netcdf_extract_metadata:
                metadata["attributes"] = {k: str(v) for k, v in ds.attrs.items()}

            # Extract variable information
            variables_info = []
            for var_name in ds.data_vars:
                var = ds[var_name]
                var_info = {
                    "name": var_name,
                    "dimensions": list(var.dims),
                    "shape": list(var.shape),
                    "dtype": str(var.dtype),
                    "attributes": {k: str(v) for k, v in var.attrs.items()}
                }

                # Sample data if enabled
                if self.netcdf_sample_arrays:
                    # Get a small sample
                    sample = var.values.flatten()[:self.netcdf_max_sample]
                    var_info["sample_values"] = sample.tolist()

                    # Statistics
                    try:
                        var_info["statistics"] = {
                            "min": float(var.min()),
                            "max": float(var.max()),
                            "mean": float(var.mean())
                        }
                    except:
                        pass

                variables_info.append(var_info)

            # Generate description
            description = self._generate_netcdf_description(metadata, variables_info)

            ds.close()

            return {
                "metadata": metadata,
                "variables": variables_info,
                "description": description,
                "text_for_embedding": description
            }

        except Exception as e:
            logger.error(f"Error extracting NetCDF: {e}")
            raise

    async def extract_hdf5(self, file_path: str) -> Dict[str, Any]:
        """Extract data from HDF5 files."""
        try:
            import h5py

            result = {
                "metadata": {
                    "format": "HDF5",
                    "filename": Path(file_path).name
                },
                "datasets": [],
                "groups": []
            }

            def extract_dataset_info(name, obj):
                if isinstance(obj, h5py.Dataset):
                    info = {
                        "path": name,
                        "shape": obj.shape,
                        "dtype": str(obj.dtype),
                        "attributes": {k: str(v) for k, v in obj.attrs.items()}
                    }

                    # Sample data
                    if self.netcdf_sample_arrays and obj.size > 0:
                        sample = obj[...].flatten()[:self.netcdf_max_sample]
                        info["sample_values"] = sample.tolist()

                    result["datasets"].append(info)

                elif isinstance(obj, h5py.Group):
                    info = {
                        "path": name,
                        "attributes": {k: str(v) for k, v in obj.attrs.items()}
                    }
                    result["groups"].append(info)

            with h5py.File(file_path, 'r') as f:
                # Extract global attributes
                result["metadata"]["attributes"] = {k: str(v) for k, v in f.attrs.items()}

                # Traverse all datasets and groups
                f.visititems(extract_dataset_info)

            # Generate description
            description = self._generate_hdf5_description(result)
            result["description"] = description
            result["text_for_embedding"] = description

            return result

        except Exception as e:
            logger.error(f"Error extracting HDF5: {e}")
            raise

    async def extract_parquet(self, file_path: str) -> Dict[str, Any]:
        """Extract data from Parquet files."""
        try:
            import pandas as pd

            df = pd.read_parquet(file_path)

            metadata = {
                "format": "Parquet",
                "filename": Path(file_path).name,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }

            # Sample and statistics (same as CSV)
            sample_data = df.head(self.csv_sample_rows).to_dict(orient='records')

            statistics = {}
            if self.csv_include_stats:
                numeric_cols = df.select_dtypes(include=['number']).columns
                for col in numeric_cols:
                    statistics[col] = {
                        "mean": float(df[col].mean()),
                        "std": float(df[col].std()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max())
                    }

            description = self._generate_csv_description(df, metadata, statistics)

            return {
                "metadata": metadata,
                "statistics": statistics,
                "sample_data": sample_data,
                "description": description,
                "text_for_embedding": description
            }

        except Exception as e:
            logger.error(f"Error extracting Parquet: {e}")
            raise

    async def extract(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from scientific file.

        Args:
            file_path: Path to scientific data file

        Returns:
            Dict with metadata, data, and text for embedding
        """
        if not self.enabled:
            return None

        filename = Path(file_path).name
        if not self.is_scientific_data_file(filename):
            return None

        ext = Path(filename).suffix.lower().lstrip(".")

        try:
            if ext in ["csv", "tsv"]:
                return await self.extract_csv(file_path)
            elif ext in ["xlsx", "xls"]:
                return await self.extract_excel(file_path)
            elif ext in ["nc", "netcdf"]:
                return await self.extract_netcdf(file_path)
            elif ext in ["hdf5", "h5"]:
                return await self.extract_hdf5(file_path)
            elif ext == "parquet":
                return await self.extract_parquet(file_path)
            else:
                logger.warning(f"Unsupported scientific data format: {ext}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract scientific data from {filename}: {e}")
            return None

    # Helper methods for generating semantic descriptions

    def _generate_csv_description(self, df, metadata, statistics) -> str:
        """Generate semantic description of CSV data."""
        desc = f"CSV dataset: {metadata['filename']}\n"
        desc += f"Contains {metadata['rows']} rows and {metadata['columns']} columns.\n\n"
        desc += f"Columns: {', '.join(metadata['column_names'])}\n\n"

        if statistics:
            desc += "Statistical Summary:\n"
            for col, stats in statistics.items():
                desc += f"- {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, "
                desc += f"range=[{stats['min']:.2f}, {stats['max']:.2f}]\n"

        return desc

    def _generate_excel_description(self, sheets_data) -> str:
        """Generate semantic description of Excel data."""
        desc = f"Excel workbook with {len(sheets_data)} sheet(s).\n\n"

        for sheet in sheets_data:
            desc += f"Sheet '{sheet['sheet_name']}':\n"
            desc += f"- {sheet['rows']} rows × {sheet['columns']} columns\n"
            desc += f"- Columns: {', '.join(sheet['column_names'])}\n\n"

        return desc

    def _generate_netcdf_description(self, metadata, variables_info) -> str:
        """Generate semantic description of NetCDF data."""
        desc = f"NetCDF dataset: {metadata['filename']}\n"
        desc += f"Dimensions: {metadata['dimensions']}\n"
        desc += f"Variables: {', '.join(metadata['variables'])}\n\n"

        for var in variables_info:
            desc += f"Variable '{var['name']}':\n"
            desc += f"- Dimensions: {var['dimensions']}\n"
            desc += f"- Shape: {var['shape']}\n"
            if "statistics" in var:
                stats = var["statistics"]
                desc += f"- Range: [{stats['min']:.2f}, {stats['max']:.2f}], Mean: {stats['mean']:.2f}\n"
            desc += "\n"

        return desc

    def _generate_hdf5_description(self, result) -> str:
        """Generate semantic description of HDF5 data."""
        desc = f"HDF5 file: {result['metadata']['filename']}\n"
        desc += f"Contains {len(result['datasets'])} dataset(s) and {len(result['groups'])} group(s).\n\n"

        for dataset in result["datasets"][:10]:  # Limit to first 10
            desc += f"Dataset '{dataset['path']}':\n"
            desc += f"- Shape: {dataset['shape']}, Type: {dataset['dtype']}\n"

        return desc


# Global instance
_scientific_extractor: Optional[ScientificDataExtractor] = None


def get_scientific_extractor() -> ScientificDataExtractor:
    """Get or create global scientific data extractor instance."""
    global _scientific_extractor

    if _scientific_extractor is None:
        _scientific_extractor = ScientificDataExtractor()

    return _scientific_extractor
