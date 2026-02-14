
try:
    import opik
    from opik import Opik
    import inspect
    
    with open("opik_signatures.txt", "w") as f:
        f.write(f"Opik version: {getattr(opik, '__version__', 'unknown')}\n")
        
        # Inspect Opik constructor
        f.write("\nOpik.__init__ signature:\n")
        try:
            f.write(str(inspect.signature(Opik.__init__)))
        except Exception as e:
            f.write(f"Error: {e}")
            
        client = Opik(api_key="mock_key")
        trace = client.trace(name="test")
        
        # Inspect log_feedback_score
        f.write("\n\nTrace.log_feedback_score signature:\n")
        try:
            f.write(str(inspect.signature(trace.log_feedback_score)))
            f.write("\nDoc:\n")
            f.write(str(trace.log_feedback_score.__doc__))
        except Exception as e:
            f.write(f"Error: {e}")

except ImportError:
    with open("opik_signatures.txt", "w") as f:
        f.write("Opik not installed")
except Exception as e:
    with open("opik_signatures.txt", "w") as f:
        f.write(f"Error: {e}")
