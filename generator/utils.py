"""CLI utilities."""


def flush_input():
    """Flush stdin buffer to prevent type-ahead from auto-answering prompts."""
    try:
        import msvcrt

        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        try:
            import sys
            import termios

            termios.tcflush(sys.stdin, termios.TCIOFLUSH)
        except (ImportError, Exception):
            pass
