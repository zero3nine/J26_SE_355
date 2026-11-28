from sentence_transformers import SentenceTransformer


class SemanticEmbedder:
    """Generate semantic embeddings using a local Sentence Transformer."""

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        revision: str | None = None,
    ):
        self.model_name = model_name
        self.model_revision = revision or (self.DEFAULT_REVISION if model_name == self.DEFAULT_MODEL else None)
        self.model = SentenceTransformer(model_name, revision=self.model_revision)

    def encode(
        self,
        texts: str | list[str],
    ):
        return self.model.encode(
            texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
