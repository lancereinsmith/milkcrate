"""Run entrypoint for milkcrate using the core factory."""

from milkcrate_core import create_app

app = create_app()


def main() -> None:
    """Run the development server."""
    app.run(debug=True, host="0.0.0.0", port=5001)


if __name__ == "__main__":
    main()
