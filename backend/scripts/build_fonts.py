"""Rebuild the bundled mixed-script font with fonttools==4.60.1 (development only)."""

from pathlib import Path

from fontTools.merge import Merger


def main() -> None:
    fonts = Path(__file__).resolve().parents[1] / "app" / "reporting" / "fonts"
    font = Merger().merge(
        [str(fonts / "NotoSans-Regular.ttf"), str(fonts / "NotoSansDevanagari-Regular.ttf")]
    )
    font.save(str(fonts / "ChakravyuhNoto-Regular.ttf"))


if __name__ == "__main__":
    main()
