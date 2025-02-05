from semantic_kernel.functions import kernel_function


class ExamplePlugin:
    """
    Demonstrates how to define plugin methods for function-calling usage
    (e.g. retrieving data from Cosmos DB, performing search, etc.).

    The @kernel_function decorator is used to let Semantic Kernel know
    these methods can be auto-invoked by the LLM (if your agent's
    function choice behavior is set to 'Auto()').
    """

    @kernel_function(description="Retrieve custom 'rules' or data from an external system.")
    def get_rules(self, query: str) -> str:
        """
        Placeholder for a call to an external DB or service (e.g. Cosmos).
        Returns a mock string with rules for demonstration.
        """
        return f"Mocked rules for query: {query}"

    @kernel_function(description="Returns a random 'score' for demonstration.")
    def get_score(self) -> str:
        """Pretends to generate some score from external data."""
        import random

        return str(random.randint(1, 100))
