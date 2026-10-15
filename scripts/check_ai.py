"""Check the OpenAI connection with a short request."""

from openai import OpenAI, OpenAIError

from app.config import Settings


def main() -> None:
    """Verify that the configured model can answer a request."""
    settings = Settings()

    if (
        settings.openai_api_key is None
        or not settings.openai_api_key.get_secret_value()
    ):
        print("Add OPENAI_API_KEY to your .env file first.")
        return

    try:
        with OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=30.0,
            max_retries=0,
        ) as client:
            response = client.responses.create(
                model=settings.openai_model,
                input="Reply exactly: AI connection works.",
                max_output_tokens=32,
                store=False,
            )

            print(response.output_text)

    except OpenAIError as error:
        print(f"AI connection failed: {type(error).__name__}")
        print(f"Error code: {getattr(error, 'code', None)}")


if __name__ == "__main__":
    main()
