import pandas as pd

def parse_job_description(jd_text):
    """Parse job description text into structured format"""
    lines = jd_text.strip().split('\n')
    
    job_requirements = {
        'role': '',
        'required_skills': [],
        'required_years': 0,
        'required_certifications': [],
        'education_requirement': '',
    }
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        lower_line = line.lower()
        
        if 'role:' in lower_line:
            job_requirements['role'] = line.split(':', 1)[1].strip()
        elif 'required skills:' in lower_line:
            current_section = 'skills'
        elif 'experience:' in lower_line:
            try:
                years = int(''.join(filter(str.isdigit, line)))
                job_requirements['required_years'] = years
            except:
                pass
        elif 'certifications:' in lower_line:
            current_section = 'certifications'
        elif current_section == 'skills' and line.startswith('-'):
            job_requirements['required_skills'].append(line.strip('- '))
        elif current_section == 'certifications' and line.startswith('-'):
            job_requirements['required_certifications'].append(line.strip('- '))
    
    return job_requirements

def prepare_export_data(results):
    """Prepare evaluation results for CSV export"""
    export_df = pd.DataFrame(results)
    export_df = export_df.round(2)
    export_df['status'] = export_df['overall_score'].apply(
        lambda x: 'Highly Suitable' if x >= 80 
        else 'Suitable' if x >= 60 
        else 'Not Suitable'
    )
    return export_df
