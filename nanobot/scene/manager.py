"""Scene manager for ChatBI."""
from pathlib import Path
from typing import Any

from nanobot.scene.config import SceneConfig, DEFAULT_SCENES


class SceneManager:
    """Manager for ChatBI scenes."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._scenes: dict[str, SceneConfig] = {}
        self._config_path = config_path
        self._load_scenes()

    def _load_scenes(self) -> None:
        """Load scene configurations."""
        # Load default scenes
        self._scenes.update(DEFAULT_SCENES)
        
        # TODO: Load custom scenes from config file
        if self._config_path and self._config_path.exists():
            # Implement JSON/YAML loading here
            pass

    def get_scene(self, scene_code: str) -> SceneConfig | None:
        """Get scene configuration by code."""
        return self._scenes.get(scene_code)

    def list_scenes(self) -> list[dict[str, Any]]:
        """List all available scenes."""
        return [
            {
                "scene_code": scene.scene_code,
                "scene_name": scene.scene_name,
                "description": scene.description,
                "enabled_skills": scene.enabled_skills,
            }
            for scene in self._scenes.values()
        ]

    def register_scene(self, scene: SceneConfig) -> None:
        """Register a new scene."""
        self._scenes[scene.scene_code] = scene

    def get_enabled_skills(self, scene_code: str) -> list[str]:
        """Get enabled skills for a scene."""
        scene = self.get_scene(scene_code)
        return scene.enabled_skills if scene else []
