from pydantic import BaseModel


class CourseOut(BaseModel):
    id: str
    title: str


class CourseOfferingOut(BaseModel):
    id: str
    course_id: str
