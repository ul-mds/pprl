from faker import Faker
from pprl_model import AttributeValueEntity


def generate_person(person_id: str, faker: Faker):
    return AttributeValueEntity(
        id=person_id,
        attributes={
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "date_of_birth": faker.date_of_birth(minimum_age=18, maximum_age=120).strftime("%Y-%m-%d"),
            "gender": faker.random_element(["male", "female"])
        }
    )
