from src.Presentation import theme


def test_builtin_themes_are_available() -> None:
    assert "cherry_dark" in theme.available_themes()
    assert "cherry_light" in theme.available_themes()


def test_theme_proxy_tracks_selected_theme() -> None:
    original = theme.get_theme_name()
    try:
        theme.set_theme("cherry_light")
        assert theme.THEME["name"] == "cherry_light"
        assert theme.THEME["background"] == theme.get_theme("cherry_light")["background"]

        theme.set_theme("cherry_dark")
        assert theme.THEME["name"] == "cherry_dark"
        assert theme.is_dark_theme() is True
    finally:
        theme.set_theme(original)


def test_invalid_theme_fails_clearly() -> None:
    try:
        theme.set_theme("not-a-theme")
    except ValueError as exc:
        assert "Available themes" in str(exc)
    else:
        raise AssertionError("Expected ValueError for an unknown theme")


def test_nicegui_css_uses_active_theme_tokens() -> None:
    css = theme.build_nicegui_css(theme.get_theme("cherry_dark"))
    assert theme.get_theme("cherry_dark")["background"] in css
    assert theme.get_theme("cherry_dark")["primary"] in css
    assert "--ag-background-color" in css


def test_light_theme_disables_dark_mode() -> None:
    assert theme.is_dark_theme("cherry_light") is False
