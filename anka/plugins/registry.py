# -*- coding: utf-8 -*-
"""ANKA AI Modüler Plugin Registry & Dahili Yetenekler."""

import logging
from typing import Any, Dict, List, Optional
from anka.plugins.base import BasePlugin

logger = logging.getLogger("anka.plugins.registry")


class WeatherPlugin(BasePlugin):
    """Hava Durumu Yeteneği Eklentisi."""

    def __init__(self):
        super().__init__(
            name="WeatherSkill",
            description="Şehir bazlı canlı hava durumu bilgisi sunar.",
        )

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> bool:
        return True

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        city = params.get("city", "İstanbul")
        return {"status": "success", "plugin": self.name, "city": city, "action": action}


class MediaControlPlugin(BasePlugin):
    """Spotify & YouTube Medya Kontrol Yeteneği Eklentisi."""

    def __init__(self):
        super().__init__(
            name="MediaControlSkill",
            description="Spotify ve YouTube medya oynatım ve şarkı arama kontrolleri.",
        )

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> bool:
        return True

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        service = params.get("service", "youtube")
        return {"status": "success", "plugin": self.name, "service": service, "query": query, "action": action}


class CalendarPlugin(BasePlugin):
    """Takvim ve Etkinlik Yönetim Yeteneği Eklentisi."""

    def __init__(self):
        super().__init__(
            name="CalendarSkill",
            description="Takvim etkinliklerini listeleme ve ajanda takibi.",
        )

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> bool:
        return True

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        event = params.get("event", "")
        return {"status": "success", "plugin": self.name, "event": event, "action": action}


class SystemToolsPlugin(BasePlugin):
    """Sistem Araçları Yeteneği Eklentisi."""

    def __init__(self):
        super().__init__(
            name="SystemToolsSkill",
            description="Ekran görüntüsü alma, IP ve sistem durumu sorgulama.",
        )

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> bool:
        return True

    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "plugin": self.name, "action": action}


class PluginRegistry:
    """Tüm ANKA Yetenek/Plugin modüllerini yöneten merkezi kayıt defteri."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._load_default_plugins()

    def _load_default_plugins(self) -> None:
        defaults = [
            WeatherPlugin(),
            MediaControlPlugin(),
            CalendarPlugin(),
            SystemToolsPlugin(),
        ]
        for plugin in defaults:
            self.register(plugin)

    def register(self, plugin: BasePlugin) -> bool:
        """Yeni bir eklenti kaydeder."""
        if plugin.name in self._plugins:
            logger.warning("Plugin '%s' zaten kayıtlı. Güncelleniyor...", plugin.name)
        try:
            if plugin.initialize():
                self._plugins[plugin.name] = plugin
                logger.info("Plugin '%s' başarıyla yüklendi.", plugin.name)
                return True
        except Exception as exc:
            logger.error("Plugin '%s' yüklenirken hata: %s", plugin.name, exc)
        return False

    def unregister(self, name: str) -> bool:
        """Kayıtlı eklentiyi kaldırır."""
        if name in self._plugins:
            try:
                self._plugins[name].shutdown()
            except Exception:
                pass
            del self._plugins[name]
            return True
        return False

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "enabled": p.enabled,
            }
            for p in self._plugins.values()
        ]

    def execute_action(self, plugin_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {"status": "error", "message": f"Plugin '{plugin_name}' bulunamadı."}
        if not plugin.enabled:
            return {"status": "error", "message": f"Plugin '{plugin_name}' devre dışı."}
        return plugin.execute(action, params)
