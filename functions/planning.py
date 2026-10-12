from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from layers.config import get_settings

from prompts import PLAN_REVISION_PROMPT,PROBLEM_ANALYSIS_PROMPT,PLAN_VALIDATION_PROMPT,PROBLEM_PLANNING_PROMPT

class ProblemAnalysis(BaseModel):
    goal: str = Field(description="Main goal of the user")
    requirements: list[str] = Field(description="Important requirements")
    constraints: list[str] = Field(description="Limitations or rules")
    missing_information: list[str] = Field(
        description="Information required before completing the task"
    )


class Task(BaseModel):
    task_id: int
    title: str
    description: str
    depends_on: list[int] = Field(
        description="Task IDs that must finish before this task"
    )


class ProblemPlan(BaseModel):
    tasks: list[Task]
    final_output: str


class PlanValidation(BaseModel):
    is_valid: bool = Field(description="True if the plan is correct")
    missing_steps: list[str]
    risks: list[str]
    improvement: str


class ProblemBreaker:
    def __init__(self):
        settings = get_settings()

        self.llm = ChatOpenAI(
            model=settings.base_model,
            api_key=settings.openai_api_key
        )

        self.analysis_llm = self.llm.with_structured_output(ProblemAnalysis)
        self.plan_llm = self.llm.with_structured_output(ProblemPlan)
        self.validation_llm = self.llm.with_structured_output(PlanValidation)

    def analyze_problem(self, user_request: str) -> ProblemAnalysis:
        return self.analysis_llm.invoke(
            f"""
{PROBLEM_ANALYSIS_PROMPT}
User request:
{user_request}
"""
        )

    def make_plan(self, analysis: ProblemAnalysis) -> ProblemPlan:
        return self.plan_llm.invoke(
            f"""
{PROBLEM_PLANNING_PROMPT}
Goal:
{analysis.goal}

Requirements:
{analysis.requirements}

Constraints:
{analysis.constraints}

Make small tasks. Add dependencies only when needed.
"""
        )

    def validate_plan(
        self,
        plan: ProblemPlan,
        analysis: ProblemAnalysis
    ) -> PlanValidation:
        return self.validation_llm.invoke(
            f"""
{PLAN_VALIDATION_PROMPT}
Goal:
{analysis.goal}

Requirements:
{analysis.requirements}

Plan:
{plan.model_dump_json()}

Find missing steps, risks, and improvements.
"""
        )

    def revise_plan(
        self,
        old_plan: ProblemPlan,
        analysis: ProblemAnalysis,
        validation: PlanValidation
    ) -> ProblemPlan:
        return self.plan_llm.invoke(
            f"""
{PLAN_REVISION_PROMPT}

Goal:
{analysis.goal}

Old plan:
{old_plan.model_dump_json()}

Validation:
{validation.model_dump_json()}

Fix all missing steps and risks.
"""
        )


def createPlan(query: str) -> ProblemPlan:
    breaker = ProblemBreaker()

    analysis = breaker.analyze_problem(query)
    plan = breaker.make_plan(analysis)
    validation = breaker.validate_plan(plan, analysis)

    if validation.is_valid:
        return plan

    return breaker.revise_plan(
        old_plan=plan,
        analysis=analysis,
        validation=validation
    )