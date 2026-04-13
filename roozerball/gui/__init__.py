"""Roozerball GUI entry points."""

__all__ = ["launch", "RoozerballApp"]


def __getattr__(name: str):
    if name in {"launch", "RoozerballApp"}:
        from roozerball.gui.app import RoozerballApp, launch

        return {"launch": launch, "RoozerballApp": RoozerballApp}[name]
    raise AttributeError(name)
