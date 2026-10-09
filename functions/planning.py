from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from layers.config import get_settings


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
Analyze this user request.

Find:
- Main goal
- Requirements
- Constraints
- Missing information

User request:
{user_request}
"""
        )

    def make_plan(self, analysis: ProblemAnalysis) -> ProblemPlan:
        return self.plan_llm.invoke(
            f"""
Create an ordered execution plan from this analysis.

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
Check whether this plan can complete the user's goal.

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
Create an improved final plan.

Goal:
{analysis.goal}

Old plan:
{old_plan.model_dump_json()}

Validation:
{validation.model_dump_json()}

Fix all missing steps and risks.
"""
        )


def create_final_plan(query: str) -> ProblemPlan:
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