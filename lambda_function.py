import json
from os import environ
from kydashboardupdater import KYDashboardUpdater
from gdh2auth.gdh2auth import GDH2Auth

csv_path = r'/home/jm/ky-dashboard-updater/scratch/test.csv'

# def lambda_handler(event, context):
def lambda_handler():
    
    gdh2_authy = GDH2Auth(realm=environ.get('REALM'), 
                 user=environ.get('USER'), 
                 secret=environ.get('SECRET'),
                 client_id=environ.get('CLIENT_ID'),
                 client_secret=environ.get('CLIENT_SECRET'))

    ky_dash = KYDashboardUpdater(gdh2_auth_session=gdh2_authy.get_session(), baseUrl=f"https://{environ['REALM']}.gdh.geocomm.cloud", pid=environ['GROUP'])
    ky_dash.connect_to_portal(environ.get('PORTAL'), environ.get('PORTAL_USER'), environ.get('PORTAL_SECRET'))

    agencies =  ky_dash.get_agencies()

    report = ky_dash.get_report(agencies)
    
    ky_dash.push_report_to_csv(report, csv_path)
    # results = ky_dash.update_dashboard(report, agencies)

    return {
        'statusCode': 200,
        'body': json.dumps('Updated KY Dashboard Successfully'),
    }



