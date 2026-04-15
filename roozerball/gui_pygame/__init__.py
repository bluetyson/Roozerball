"""Roozerball Pygame GUI entry points (Tier 2 graphics)."""

__all__ = ["launch", "PygameApp"]


def __getattr__(name: str):
    if name in {"launch", "PygameApp"}:
        from roozerball.gui_pygame.app import PygameApp, launch

        return {"launch": launch, "PygameApp": PygameApp}[name]
    raise AttributeError(name)
