from pydantic import BaseModel, ConfigDict


class ExperienceItem(BaseModel):
    title: str = ""
    company: str = ""
    dates: str = ""
    description: str = ""


class ProjectItem(BaseModel):
    title: str = ""
    dates: str = ""
    technologies: str = ""
    description: str = ""


class ProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    location: str = ""
    open_to_remote: bool = True
    years_experience: float = 0
    target_titles: list[str] = []
    summary: str = ""
    skills: list[str] = []
    experience: list[ExperienceItem] = []
    projects: list[ProjectItem] = []
    education: list[str] = []
    certifications: list[str] = []
    languages: list[str] = []


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
