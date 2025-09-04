"""ABM Data Configuration Component for LangFlow."""

from __future__ import annotations

import os
from pathlib import Path

from langflow.custom import Component
from langflow.io import BoolInput, Output, StrInput
from langflow.schema import Data


class ABMDataConfig(Component):
    display_name = "ABM Data Config"
    description = "Configure data paths and settings for ABM audiobook processing"
    icon = "settings"
    name = "ABMDataConfig"

    inputs = [
        StrInput(
            name="data_root",
            display_name="Data Root Directory",
            info="Root directory containing all audiobook data",
            value=os.getenv("ABM_DATA_ROOT", str(Path.cwd() / "data")),
            required=True,
        ),
        StrInput(
            name="book_id",
            display_name="Book ID",
            info="Identifier for the book (e.g., 'mvs')",
            value="mvs",
            required=True,
        ),
        BoolInput(
            name="validate_paths",
            display_name="Validate Paths",
            info="Check if data directories exist",
            value=True,
        ),
    ]

    outputs = [Output(name="config_data", display_name="Configuration Data", method="build_config")]

    def build_config(self):
        """Build data configuration for audiobook processing."""
        try:
            data_root = Path(self.data_root)

            # Build standard paths
            config = {
                "data_root": str(data_root),
                "book_id": self.book_id,
                "books_dir": str(data_root / "books" / self.book_id),
                "clean_dir": str(data_root / "clean" / self.book_id),
                "annotations_dir": str(data_root / "annotations" / self.book_id),
                "volume_manifest": str(data_root / "clean" / self.book_id / f"{self.book_id}_volume.json"),
                "chapters_dir": str(data_root / "clean" / self.book_id),
            }

            # Validate paths if requested
            if self.validate_paths:
                missing_paths = []
                for key, path_str in config.items():
                    if key.endswith("_dir") or key == "data_root":
                        if not Path(path_str).exists():
                            missing_paths.append(f"{key}: {path_str}")

                if missing_paths:
                    self.status = f"⚠️ Missing paths: {', '.join(missing_paths)}"
                else:
                    self.status = "✅ All data paths validated"
            else:
                self.status = "📁 Configuration built (validation skipped)"

            return Data(data=config)

        except Exception as e:
            self.status = f"❌ Configuration failed: {str(e)}"
            return Data(data={"error": str(e)})
