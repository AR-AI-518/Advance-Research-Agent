import os
import time

from Agent import Research
from layers.cashe import Cache
from layers.config import get_settings
from layers.monitring import MetricsCollection, setup_logging
from layers.security import InputSanitizer, Validator


class Pipeline:
    def __init__(self):
        self.settings = get_settings()

        if self.settings.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langchain_project
            os.environ["LANGCHAIN_TRACING_V2"] = str(self.settings.langchain_tracing_v2).lower()

        self.logger = setup_logging()
        self.sanitizer = InputSanitizer()
        self.validator = Validator()
        self.cache = Cache()
        self.metrics = MetricsCollection()
        self.agent = Research()

    @staticmethod
    def format_result(research, validator: Validator) -> str:
        lines = [research.summary]

        if research.key_findings:
            lines.append("\nKey Findings:")
            lines.extend(f"- {item}" for item in research.key_findings)

        if research.limitations:
            lines.append("\nLimitations:")
            lines.extend(f"- {item}" for item in research.limitations)

        text = validator.harmful_response("\n".join(lines))

        sources = []
        for source in research.sources:
            for title, url in zip(source.titles, source.urls):
                sources.append(f"- {title}: {url}")

        if sources:
            text += "\n\nSources:\n" + "\n".join(sources)

        return text

    def run(self, message: str, user_id: str = "default_user", thread_id: str | None = None) -> dict:
        start = time.perf_counter()

        if self.sanitizer.check_input(message):
            self.metrics.record_request(time.perf_counter() - start, 0, 0, error=True)
            raise ValueError("Prompt injection detected")

        clean = self.sanitizer.clean_text(message)
        if not clean:
            self.metrics.record_request(time.perf_counter() - start, 0, 0, error=True)
            raise ValueError("Empty message after cleaning")

        cache_key = f"{user_id}:{thread_id}:{clean}"
        cached = self.cache.get(cache_key)
        if cached:
            elapsed = time.perf_counter() - start
            self.metrics.record_request(elapsed, 0, 0, cache_hit=True)
            return {**cached, "cached": True, "processing_time": elapsed}

        try:
            result = self.agent.invoke(clean, user_id, thread_id)

            if result["error"] or result["research_result"] is None:
                raise RuntimeError(result["error"] or "No research result returned")

            text = self.format_result(result["research_result"], self.validator)
        except Exception as e:
            elapsed = time.perf_counter() - start
            self.metrics.record_request(elapsed, 0, 0, error=True)
            self.logger.error(str(e), extra={"extract_data": {"user_id": user_id}})
            raise

        elapsed = time.perf_counter() - start
        self.metrics.record_request(
            elapsed,
            result["input_tokens"],
            result["output_tokens"]
        )

        response = {
            "response": text,
            "thread_id": result["thread_id"],
            "cached": False,
            "model_used": ", ".join(dict.fromkeys(result["model_used"])) or "unknown",
            "processing_time": elapsed
        }

        self.cache.set(cache_key, {k: v for k, v in response.items() if k != "processing_time"})

        return response

    def get_metrics(self) -> dict:
        return self.metrics.summarize()


if __name__ == "__main__":
    pipeline = Pipeline()
    output = pipeline.run("What is LangGraph?", "test_user")
    print(output["response"])