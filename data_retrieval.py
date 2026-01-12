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

with open("data/course_list.csv", newline='', encoding = 'utf-8') as csvfile:
    # Read course_list.csv + Save to course_info
    course_info : dict[str, list[str]] = {}
    # course_info : {code : [title, units]}
    
    reader = csv.DictReader(csvfile, 
                            delimiter=',',
                            fieldnames = ['code', 'title', 'units'])
    course_info = {row['code']: [row['title'], row['units']] for row in reader} 
    


with open("data/equivalence_courses.csv", newline='', encoding = 'utf-8') as csvfile:  
    reader = csv.DictReader(csvfile, 
                            delimiter=',',
                            fieldnames = ['major', 'code(hk)', 'name(hk)', 'code(sz)', 'name(sz)'])
    
    equivalence_courses: dict[str, dict[str, str]] = {major: {} for major in major_list}
    """
    equivalence_courses: {
        major : {
            code(hk) : code(sz)
        }
    }
    """
    
    for row in reader:
        # Get the equivalence course ID
        equivalence_courses[row['major']][row['code(hk)']] = row['code(sz)']
        
        
        # Add equivalence course info to course_info
        if row['code(hk)'] not in course_info.keys():
            unit = course_info[row['code(sz)']][1]
            
            course_info[row['code(hk)']] = [row['name(hk)'], unit]
        
        elif row['code(sz)'] not in course_info.keys():
            unit = course_info[row['code(hk)']][1]

            course_info[row['code(sz)']] = [row['name(sz)'], unit]
            
with open("data/course_list.json") as jsonfile:
    course_list = json.load(jsonfile)          

def get_equivalence_courses(major : str = 'all') -> dict[str, dict[str, str]] | dict[str, str]:
    if major == 'all':
        return equivalence_courses
    
    elif major not in major_list:
        print(f'"{major} Not Found" : "Please check again"')
        return {"Major Not Found" : "Please check again"}
    
    else:
        return equivalence_courses[major]

def get_course_info(request : str = "all") -> dict[str, list[str]] | list[str] :
    if request == "all":
        return course_info
    
    elif request == "id":
        return list(course_info.keys())
    
    elif request not in course_info.keys():
        print(f"Course ID {request} Not Found")
        return ["Course ID Not Found"]
    
    else:
        return course_info[request]

def get_course_list(major : str = "all") -> dict[str, str | list[str]]:
    if major == "all":
        return course_list
    elif major not in major_list:
        return {"Not Found": f"{major} Not Found"}
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

def show_course_info(major : str, course_list : str | list[str], campus : Literal['hk', 'sz'], request_type : str = "courses") -> list[str | int]:
    output_list : list[str] = []
    
    if type(course_list) == str: # Convert to list
        course_list = [course_list]
        
    for id in course_list:  
        if request_type == "credits":
            output_list.append(int(get_course_info(id)[1]))
        
        elif request_type == "courses":
            if determine_campus(id) != campus :
                id = convert_course_id(major, id)
                
                if id == "Not Found": # No substitute course
                    output_list.append("Unavailable")
                    continue
            
            output_list.append(f"{id} | {get_course_info(id)[0]}")
        else:
            return ["Error : Wrong value in parameter type"]
    return output_list
