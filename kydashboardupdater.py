from datetime import datetime
# Connect to the GIS
from arcgis.gis import GIS
from os import environ
import csv

class KYDashboardUpdater:

    def __init__(self, gdh2_auth_session: object, baseUrl: str, pid: str):

        self.gdh2_auth_session = gdh2_auth_session
        self.baseUrl = baseUrl
        self.pid = pid
        self.ky_psaps_feature_layer = None
        self.gis = None

    def connect_to_portal(self, portal_url, portal_user, portal_secret):

        if self.gis is None:

            self.gis = GIS(portal_url, portal_user, portal_secret)

        return self.gis

    def get_feature_layer(self):

        if self.ky_psaps_feature_layer is None:

            portal_feature_layer_id = environ['PORTAL_FEATURE_LAYER_ID']

            psaps = self.gis.content.get(portal_feature_layer_id)
            self.ky_psaps_feature_layer = psaps.layers[0]

        return self.ky_psaps_feature_layer

    def get_dashboard_features(self):

        # All fields
        # GDHName, Warning, Critical, LastUp, TotalUp, QuarterUp

        self.get_feature_layer()
        self.ky_psaps_features = self.ky_psaps_feature_layer.query(out_fields='*', return_geometry=False)

        return self.ky_psaps_features

    def get_agencies(self, get_dashboard_agecies=False, gdh_agency_names=None):

        agencies_url = f"{self.baseUrl}/configurations/accounts/{self.pid}/agencies"
        res = self.gdh2_auth_session.get(agencies_url)
        
        if get_dashboard_agecies is True:
            # only return agencies in the dashboard feature layer.
            agencies = {x['name']:x['id'] for x in res.json() if x['name'] in
                        [f['attributes']['GDHName'] for f in
                        self.get_dashboard_features().to_dict()['features']]}
        
        if gdh_agency_names:
            agencies = {x['name']:x['id'] for x in res.json() if x['name'] in gdh_agency_names}
        
        if gdh_agency_names is None and get_dashboard_agecies is False:
            agencies = {x['name']:x['id'] for x in res.json()}
            
        return agencies

    def get_uploads(self, aid):

        uploads_by_agency = f"{self.baseUrl}/uploads/{self.pid}/{aid}/"
        res = self.gdh2_auth_session.get(uploads_by_agency)
        
        if res.status_code == 200:

            data = res.json()

            # Get Failed Uploads
            failed_uploads = sorted([x for x in data['uploads'] if x['status'] != 'succeeded'], key=lambda x:datetime.strptime(x['created_utc'], "%Y-%m-%dT%H:%M:%S.%f"), reverse=True)
            failed_uploads_cnt = len(failed_uploads)
            failed_uploads_last_date = failed_uploads[0]['created_utc'] if failed_uploads_cnt != 0 else None

            # Get passed uploads
            pass_uploads = sorted([x for x in data['uploads'] if x['status'] == 'succeeded'], key = lambda x:datetime.strptime(x['created_utc'], "%Y-%m-%dT%H:%M:%S.%f"), reverse=True)
            pass_uploads_cnt = len(pass_uploads)
            pass_uploads_last_date = pass_uploads[0]['created_utc'] if pass_uploads_cnt != 0 else None


            return {'failed_uploads': failed_uploads_cnt,
                    'failed_uploads_last': failed_uploads_last_date,
                    'pass_uploads_cnt': pass_uploads_cnt,
                    'pass_uploads_last': pass_uploads_last_date}
        else:
            raise IOError(f"Unable to retrieve uploads from {uploads_by_agency}")


    def get_jobs(self, aid):

        job_by_agency = f"{self.baseUrl}/jobs/{self.pid}/{aid}/"
        res = self.gdh2_auth_session.get(job_by_agency)

        if res.status_code == 200:

            data = res.json()

            finished_jobs = sorted([x for x in data['jobs'] if x['status'] == 'finished'], key=lambda x: datetime.strptime(x['created_utc'], "%Y-%m-%dT%H:%M:%S.%f"),
                                 reverse=True)
            finished_jobs_cnt = len(finished_jobs)
            last_finished_jobid = finished_jobs[0]['id_'] if finished_jobs_cnt != 0 else None
            last_finished_job_date = finished_jobs[0]['finished_utc'] if finished_jobs_cnt != 0 else None


            return {
                'finished_jobs': finished_jobs_cnt,
                'last_finished_jobid': last_finished_jobid,
                'last_finished_job_date': last_finished_job_date
            }

    def get_reports(self, aid, last_job_id):

        report_by_job = f"{self.baseUrl}/reports/summary/{self.pid}/{aid}/{last_job_id}"

        res = self.gdh2_auth_session.get(report_by_job)
        
        if res.status_code == 200:

            data = res.json()

            # Get Columns and report content

            # ['layer_name', 'gp_name', 'elapsed_time', 'fallout_count', 'features_analyzed', 'sync_percent',
            #  'gp_severity_level']

            columns = data['columns']
            report_data = data['reports'][0]['report']['data']

            # Set indexes
            indx_features_analyzed = columns.index('features_analyzed')
            indx_fallout_cnt = columns.index('fallout_count')
            indx_gp_severity_level = columns.index('gp_severity_level')

            print(aid)
            print(last_job_id)

            # Get Counts
            critical_errors_cnt = sum([int(str(x[indx_fallout_cnt]).replace(",", ""))
                                       for x in report_data
                                        if x[indx_gp_severity_level] == 'critical'])

            critical_features_analyzed_cnt = sum([int(str(x[indx_features_analyzed]).replace(",", ""))
                                                  for x in report_data
                                                  if x[indx_gp_severity_level] == 'critical'])

            warning_errors_cnt = sum([int(str(x[indx_fallout_cnt]).replace(",", ""))
                                      for x in report_data
                                      if x[indx_gp_severity_level] == 'warning'])

            warning_errors_features_analyzed_cnt = sum([int(str(x[indx_features_analyzed]).replace(",", ""))
                                                        for x in report_data
                                                        if x[indx_gp_severity_level] == 'warning'])


        return {
            'critical_errors_cnt': critical_errors_cnt,
            'critical_features_analyzed_cnt': critical_features_analyzed_cnt,
            'warning_errors_cnt': warning_errors_cnt,
            'warning_errors_features_analyzed_cnt': warning_errors_features_analyzed_cnt,
        }

    def get_report_row(self, gdh_name,  aid):

        print(gdh_name)

        jobs = self.get_jobs(aid)
        uploads = self.get_uploads(aid)
        fallouts = self.get_reports(aid, jobs['last_finished_jobid'])

        #Combine all the dictionaries into one.

        return {'attributes': {
            **{'GDHName': gdh_name},
            **{'Agency_Id': aid},
            **uploads,
            **jobs,
            **fallouts}}

    def get_report(self, agencies: dict):

       return {k : self.get_report_row(k, v) for k, v in agencies.items()}

    def update_dashboard(self, report, agencies):


        # Feature Attributes
        # OBJECTID, PSAP_NAME, GDHName, Warning, Critical, LastUp, TotalUp, WarningAnalyzed, CriticalAnalyzed, LastUploadFailed, Shape__Area, Shape__Length
        #
        # report attributes
        # GDHName, Agency_Id, failed_uploads, failed_uploads_last, pass_uploads_cnt, pass_uploads_last, finished_jobs, last_finished_jobid, last_finished_job_date, critical_errors_cnt, critical_features_analyzed_cnt, warning_errors_cnt, warning_errors_features_analyzed_cnt

        
        features_to_update = []
        
        # Get FeatureSet from dashboard Feature Layer
        self.get_dashboard_features()
        
        for ky_psap in [x for x in self.ky_psaps_features.features if x.get_value('GDHName') in agencies.keys()]:
            agency_report = report.get(ky_psap.get_value('GDHName'))
            ky_psap.set_value('Warning', agency_report['attributes']['warning_errors_cnt'])
            ky_psap.set_value('Critical', agency_report['attributes']['critical_errors_cnt'])
            ky_psap.set_value('LastUp', agency_report['attributes']['pass_uploads_last'])
            ky_psap.set_value('TotalUp', agency_report['attributes']['pass_uploads_cnt'])
            ky_psap.set_value('WarningAnalyzed', agency_report['attributes']['warning_errors_features_analyzed_cnt'])
            ky_psap.set_value('CriticalAnalyzed', agency_report['attributes']['critical_features_analyzed_cnt'])
            ky_psap.set_value('LastFailUploadDate', agency_report['attributes']['failed_uploads_last'])
            features_to_update.append(ky_psap)

        results = self.ky_psaps_feature_layer.edit_features(updates=features_to_update)
        return results

    def push_report_to_csv(self, report, csv_path):

        with open(csv_path, 'w', newline='') as report_csv:
            report_csv_writer =csv.writer(report_csv, 'excel')

            report_rows = []
            for agency in report.keys():
                column_names=report[agency]['attributes'].keys()
                report_rows.append(report[agency]['attributes'])

            #Write column names
            report_csv_writer.writerow(column_names)

            for report_row in report_rows:
                report_csv_writer.writerow(report_row.values())

        return csv_path

        