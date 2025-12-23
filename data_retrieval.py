import csv
import json
from bidict import bidict
from typing import Literal

major_list = (
        "Interdisciplinary Data Analytics",
        "Information Engineering",
        "Integrated BBA", 
        "Systems Engineering and Engineering Management",
        "Mathematics",
        "Statistics (CUHK)",
        "Financial Engineering",
        "Marketing and Communication",
        "Computer Science and Engineering",
        "Electrical and Computer Engineering",
        "Mathematics and Applied Mathematics",
        "Statistics (CUHK(SZ))"
        )

def get_equivalence_courses(major : str = 'all') -> dict[str, dict[str, str]] | dict[str, str]:
    equivalence_courses: dict[str, dict[str, str]] = {major: {} for major in major_list}
    
    with open('data/equivalence_courses_id.csv', newline='', encoding = 'utf-8') as csvfile:
        reader = csv.DictReader(csvfile, 
                                delimiter=',',
                                fieldnames = ['major', 'hk_id', 'sz_id'])
        
        for row in reader:
            equivalence_courses[row['major']][row['hk_id']] = row['sz_id']
            
    if major == 'all':
        return equivalence_courses
    elif major not in major_list:
        return {"Major Not Found" : "Please check again"}
    else:
        return equivalence_courses[major]

def get_course_info(course_id : str = "all") -> dict[str, list[str]] | list[str] :
    course_info : dict[str, list[str]] = {}
    
    with open('data/course_info.csv', newline='', encoding = 'utf-8') as csvfile:
        reader = csv.DictReader(csvfile, 
                                    delimiter=',',
                                    fieldnames = ['course_id', 'name', 'units'])
        course_info = {row['course_id']: [row['name'], row['units']] for row in reader} 
        
    if course_id == "all":
        return course_info
    
    elif course_id == 'id':
        return list(course_info.keys())
    
    elif course_id not in course_info.keys():
        return ["Course ID Not Found"]
    
    else:
        return course_info[course_id]

def get_course_list(major : str = "all") -> dict[str, str | list[str]]:
    with open("data/course_list.json") as jsonfile:
        course_list = json.load(jsonfile)
    
    if major == "all":
        return course_list
    elif major not in major_list:
        return {"Major Not Found" : "Please check again"}
    else:
        return course_list[major]

def determine_campus(course_id : str) -> Literal['hk', 'sz']:
    if course_id[3].isalpha():
        return 'hk'
    else:
        return 'sz'

    
def convert_course_id(major : str, course_id : str) -> str:
    data = bidict(get_equivalence_courses(major))
    
    if course_id not in data.keys() and course_id not in data.values():
        return "Not Found"
    elif determine_campus(course_id) == "hk":
        return data[course_id]
    else:
        return data.inverse[course_id]

def show_course_info(major : str, course_list : str | list[str], campus : Literal['hk', 'sz']) -> list[str]:
    output_list : list[str] = []
    
    if type(course_list) is str: # Convert to list
        course_list = [course_list]

    for id in course_list:    
        # if id not in get_course_info("id"): # Ensure the course_id is invalid
        #     output_list.append(id + "Not Found")
        # else:
        if determine_campus(id) != campus :
            id = convert_course_id(major, id)
            if id == "Not Found":
                output_list.append("Unavailable")
                continue
            
        output_list.append(f"{id} | {get_course_info(id)[0]}")
            
    return output_list
