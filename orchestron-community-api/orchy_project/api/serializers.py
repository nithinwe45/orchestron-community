import socket
from datetime import datetime
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType as DjangoContentType
from django.contrib.auth.models import Permission as DjangoPermission
from rest_framework import serializers, viewsets,status
from rest_framework.parsers import JSONParser, MultiPartParser
from api.models import Organization, User, Project, Application, Engagement, Scan, \
	Webhook,Vulnerability, VulnerabilityEvidence,VulnerabilityRemediation, VulnerabilityEvidenceRemediation, \
	OrganizationConfiguration, JiraIssueTypes, EmailConfiguration, ORLConfig, JiraProjects
from api.validators import text_file_validator, image_file_validator, start_date_validator, end_date_validator, \
	flat_file_validator
from api.messages import *
from api import jira_utils as jira 


class OpenVulSerializer(serializers.Serializer):
	open_for = serializers.IntegerField(required=False)
	cwe = serializers.IntegerField(required=False)
	tools = serializers.CharField(required=False)
	apps = serializers.CharField(required=False)
	common_name = serializers.CharField(required=False)
	names = serializers.CharField(required=False)
	bug_id = serializers.CharField(required=False)
	bug_status = serializers.CharField(required=False)
	severity = serializers.IntegerField(required=False)


class ClosedVulSerializer(serializers.Serializer):
	cwe = serializers.IntegerField(required=False)
	count = serializers.IntegerField(required=False)
	tools = serializers.CharField(required=False)
	apps = serializers.CharField(required=False)
	common_name = serializers.CharField(required=False)
	names = serializers.CharField(required=False)
	created_on = serializers.DateTimeField(required=False)
	closed_on = serializers.DateTimeField(required=False)
	severity = serializers.IntegerField(required=False)	


class QueryParamSerializer(serializers.Serializer):
	false = serializers.BooleanField(required=False)
	true = serializers.BooleanField(required=False)
	cwe = serializers.IntegerField(required=False)
	tool = serializers.CharField(required=False)
	name = serializers.CharField(required=False)
	owasp = serializers.ChoiceField(required=False,choices=[(o,o) for o in settings.OWASP_TYPES])
	start_date = serializers.DateField(required=False)
	stop_date = serializers.DateField(required=False)
	jira_sync = serializers.BooleanField(required=False)
	severity = serializers.ChoiceField(required=False,choices=[('info','info'),('low','low'),('medium','medium'),('high','high')])


class BasePostParamSerializer(serializers.Serializer):
	name = serializers.CharField()
	cwe = serializers.IntegerField()


class RaiseJIRATicketSerializer(BasePostParamSerializer):
	issuetype = serializers.CharField()
	assignee = serializers.CharField()	

	def __init__(self, *args, **kwargs):
		super(RaiseJIRATicketSerializer, self).__init__(*args, **kwargs)
		self.user = self.context.get('request').user

	def validate_issuetype(self,data):
		jira_config = self.user.org.jiraissuetypes
		issuetype_list = jira.get_issuetypes(jira_config)
		issuetypes = [p.name for p in issuetype_list]
		if data not in issuetypes:
			raise serializers.ValidationError('Invalid issue type')
		return data

	def validate_asignee(self,data):
		jira_config = self.user.org.jiraissuetypes
		users = jira.get_users(jira_config)
		if data not in users:
			raise serializers.ValidationError('Invalid asignee')
		return data		


class AssignScansSerializer(serializers.Serializer):
	scans = serializers.ListField(child=serializers.CharField(),min_length=1)		


class BaseQueryParamSerializer(serializers.Serializer):
	stats = serializers.BooleanField(required=False)
	cwe = serializers.BooleanField(required=False)
	tool = serializers.BooleanField(required=False)
	grade = serializers.BooleanField(required=False)
	owasp = serializers.BooleanField(required=False)
	severity = serializers.BooleanField(required=False)
	opened = serializers.BooleanField(required=False)
	closed = serializers.BooleanField(required=False)
	apps = serializers.BooleanField(required=False)
	months = serializers.BooleanField(required=False)
	heatmap = serializers.BooleanField(required=False)
	ageing = serializers.BooleanField(required=False)
	avg_ageing = serializers.BooleanField(required=False)


class OrganizationQueryParamSerializer(BaseQueryParamSerializer):
	projects = serializers.BooleanField(required=False)
	users = serializers.BooleanField(required=False)


class ProjectQueryParamSerializer(BaseQueryParamSerializer):
	applications = serializers.BooleanField(required=False)	


class ApplicationsQueryParamSerializer(BaseQueryParamSerializer):
	scans = serializers.BooleanField(required=False)		
	engagements = serializers.BooleanField(required=False)		
	webhooks = serializers.BooleanField(required=False)	
	assigned = serializers.BooleanField(required=False)
	unassigned = serializers.BooleanField(required=False)


class EngagementQueryParamSerializer(serializers.Serializer):
	scans = serializers.BooleanField(required=False)	


class ScanQueryParamSerializer(BaseQueryParamSerializer):
	vuls = serializers.BooleanField(required=False)		
	user = serializers.CharField(required=False)
	cvss = serializers.FloatField(required=False,max_value=10)
	false = serializers.BooleanField(required=False)
	true = serializers.BooleanField(required=False)
	cwe = serializers.IntegerField(required=False)
	owasp = serializers.ChoiceField(required=False,choices=[(o,o) for o in settings.OWASP_TYPES])
	severity = serializers.ChoiceField(required=False,choices=[('info','info'),('low','low'),('medium','medium'),('high','high')])
	date = serializers.DateField(required=False)

	def validate_user(self, data):
		if data:
			try:
				user = User.objects.get(email=data)
			except User.DoesNotExist:
				raise serializers.ValidationError('This user does not exists')
		return data


class OrganizationSerializer(serializers.ModelSerializer):
	projects_count = serializers.SerializerMethodField()

	class Meta:
		model = Organization
		fields = ['id','name','contact','num_engagements','num_projects','num_users','num_apps','num_scans','industry','location','end_date','start_date','timezone','created_on','edited_on','logo','projects_count']
		read_only_fields = ['created_on','edited_on','start_date','projects_count']	

	def validate_end_date(self,data):
		return end_date_validator(data)		

	def get_projects_count(self,obj):
		return obj.project_set.count()


class OrganizationConfigurationSerializer(serializers.ModelSerializer):
	class Meta:
		model = OrganizationConfiguration
		fields = ['enable_jira','enable_email','org','created_on','edited_on','enable_orl']
		read_only_fields = ['created_on','edited_on','org']


class JiraIssueTypesSerializer(serializers.ModelSerializer):
	class Meta:
		model = JiraIssueTypes
		fields = ['url','username','password','created_on','edited_on','org']
		read_only_fields = ['created_on','edited_on','org']	

	def __init__(self, *args, **kwargs):
		super(JiraIssueTypesSerializer, self).__init__(*args, **kwargs)


class JiraConnectionTestSerializer(serializers.Serializer):
	url = serializers.URLField()		
	username = serializers.CharField()
	password = serializers.CharField(style={'input_type': 'password'})

	class Meta:
		fields = ['url','username','password']
	

class EmailConfigurationSerializer(serializers.ModelSerializer):
	class Meta:
		model = EmailConfiguration
		fields = ['host','username','password','port','from_email','display_name','certs','created_on','edited_on','org']
		read_only_fields = ['created_on','edited_on','org']	

	def __init__(self, *args, **kwargs):
		super(EmailConfigurationSerializer, self).__init__(*args, **kwargs)


class ORLConfigSerializer(serializers.ModelSerializer):
	class Meta:
		model = ORLConfig
		fields = ['host','port','protocol','created_on','edited_on','org']
		read_only_fields = ['created_on','edited_on','org']	

	def __init__(self, *args, **kwargs):
		super(ORLConfigSerializer, self).__init__(*args, **kwargs)

	def validate_host(self, data):
		try:
			socket.gethostbyname(data)
		except:
			raise serializers.ValidationError('Invalid host name')
		return data	

	def validate_port(self, data):
		try:
			data = int(data)
			if data >= 65535:
				raise serializers.ValidationError('Invalid port number')								
		except:
			raise serializers.ValidationError('Invalid port number')
		return data	


class UserSerializer(serializers.ModelSerializer):

	class Meta:
		model = User
		fields = ['id','email','first_name','last_name','is_staff','is_admin','org','last_login']
		read_only_fields = ['last_login']

	def __init__(self, *args, **kwargs):
		super(UserSerializer, self).__init__(*args, **kwargs)


class UserProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['email','first_name','last_name','last_login','img']
		read_only_fields = ['last_login']			


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True,style={'input_type': 'password'})
    new_password = serializers.CharField(required=True,style={'input_type': 'password'})

    def validate_new_password(self,data):
    	validate_password(data)
    	return data


class SuperUserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id','email','first_name','last_name','is_staff','is_superuser','org','created_on','edited_on']	
		read_only_fields = ['created_on','edited_on']	

	def __init__(self, *args, **kwargs):
		super(SuperUserSerializer, self).__init__(*args, **kwargs)


class ProjectSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,JSONParser)

	class Meta:
		model = Project
		fields = ['id','name','org','objective','logo','created_on','edited_on','created_by']
		read_only_fields = ['created_on','edited_on','created_by']

	def __init__(self, *args, **kwargs):
		super(ProjectSerializer, self).__init__(*args, **kwargs)


class ApplicationSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,JSONParser)
	# project_details = serializers.SerializerMethodField()
	# org_details = serializers.SerializerMethodField()

	class Meta:
		model = Application
		fields = ['id','name','ipv4','os_info','host_type','org','project','url','logo','platform_tags','created_on','edited_on','created_by']
		read_only_fields = ['created_on','edited_on','created_by']

	def __init__(self, *args, **kwargs):
		super(ApplicationSerializer, self).__init__(*args, **kwargs)

	def get_project_details(self, obj):
		return ProjectSerializer(obj.project,context=self.context).data

	def get_org_details(self, obj):
		return OrganizationSerializer(obj.org,context=self.context).data


class EngagementSerializer(serializers.ModelSerializer):
	severity = serializers.SerializerMethodField()
	parser_classes = (JSONParser,)
	app_details = serializers.SerializerMethodField()

	class Meta:
		model = Engagement
		fields = ['id','name','application','description','start_date','stop_date','closed_on','closed_by',\
		'created_on','edited_on','created_by','severity','uniq_id','app_details']
		read_only_fields = ['created_on','edited_on','created_by','uniq_id','closed_on','closed_by','severity','app_details']

	def __init__(self, *args, **kwargs):
		super(EngagementSerializer, self).__init__(*args, **kwargs)

	def get_app_details(self, obj):
		return ApplicationSerializer(obj.application,context=self.context).data		

	def get_severity(self,obj):
		from api.analytics import OpenVulnerabilityStatView
		kwargs = {
			'scan__engagements':obj
		}
		return OpenVulnerabilityStatView().severity_count(kwargs=kwargs)	

	def validate_start_date(self,data):
		return start_date_validator(data)				

	def validate(self, data):
		if data.get('start_date') >= data.get('stop_date'):
			raise serializers.ValidationError(ENG_START_DATE_END_DATE_VALIDATION)
		return data				


class ScanSerializer(serializers.ModelSerializer):
	parser_classes = (JSONParser,)
	tool = serializers.ChoiceField(required=False,choices=[(t,t) for t in settings.WEBHOOK_TOOLS.keys()])
	application_name = serializers.SerializerMethodField()
	triggered_by = serializers.SerializerMethodField()

	class Meta:
		model = Scan
		fields = ['id','short_name','application','tool','scan_type','engagements','name','created_on','edited_on','created_by','application_name','triggered_by']
		read_only_fields = ['created_on','edited_on','created_by','name','tool','scan_type']

	def __init__(self, *args, **kwargs):
		super(ScanSerializer, self).__init__(*args, **kwargs)

	def validate_scan_type(self, data):
		if data != 'Manual':
			raise serializers.ValidationError('Invalid Option')
		return data

	def get_application_name(self, obj):
		return obj.application.name

	def get_triggered_by(self, obj):
		if obj.created_by:
			return User.objects.get(pk=obj.created_by).username
		return 'Admin'


class WebhookSerializer(serializers.ModelSerializer):
	tool = serializers.ChoiceField(choices=[(t,t) for t in settings.WEBHOOK_TOOLS.keys()])
	parser_classes = (JSONParser,)

	class Meta:
		model = Webhook
		fields = ['name','application','tool','hook_id','created_on','edited_on']	
		read_only_fields = ['created_on','edited_on','hook_id']

	def __init__(self, *args, **kwargs):
		super(WebhookSerializer, self).__init__(*args, **kwargs)


class ParserSerializer(serializers.Serializer):
	parser_classes = (MultiPartParser,)
	name = serializers.CharField()
	tool = serializers.ChoiceField(choices=[(t,t) for t in settings.WEBHOOK_TOOLS.keys()])
	file = serializers.FileField()

	class Meta:
		fields = ['name','tool','file']	

	def validate_file(self, data):
		return flat_file_validator(data)


class JiraProjectsSerializer(serializers.ModelSerializer):
	parser_classes = (JSONParser,)

	class Meta:
		model = JiraProjects
		fields = ['name','key','jira_config','application','created_on','edited_on']	
		read_only_fields = ['created_on','edited_on','application','jira_config','key']

	def __init__(self, *args, **kwargs):
		super(JiraProjectsSerializer, self).__init__(*args, **kwargs)	
		self.user = self.context.get('request').user

	def validate(self, data):
		name = data.get('name')		
		jira_config = self.user.org.jiraissuetypes
		project_list = jira.get_projects(jira_config)
		projects = {p.name:p.key for p in project_list}
		if name not in projects.keys():
			raise serializers.ValidationError('Invalid option')
		else:
			data['key'] = projects.get(name)
		return data


class VulnerabilitySerializer(serializers.ModelSerializer):
	parser_classes = (JSONParser,)
	scan_details = serializers.SerializerMethodField()
	app_details = serializers.SerializerMethodField()

	class Meta:
		model = Vulnerability
		fields = ['id','name','description','remediation','tool','confidence','severity','vul_type','owasp','cvss','cwe',\
		'scan_details','is_false_positive','scan','is_remediated','jira_id','jira_issue_status','dread','common_name',\
		'created_on','edited_on','app_details']
		read_only_fields = ['created_on','edited_on','tool','common_name','dread','scan_details','app_details']

	def __init__(self, *args, **kwargs):
		super(VulnerabilitySerializer, self).__init__(*args, **kwargs)

	def get_scan_details(self, obj):
		return ScanSerializer(obj.scan,context=self.context).data

	def get_app_details(self, obj):
		return ApplicationSerializer(obj.scan.application,context=self.context).data


class VulnerabilityEvidenceSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,JSONParser)
	log = serializers.FileField(required=False)
	request = serializers.FileField(required=False)
	response = serializers.FileField(required=False)
	file = serializers.FileField(required=False)

	class Meta:
		model = VulnerabilityEvidence
		fields = '__all__'
		read_only_fields = ['created_on','edited_on','is_remediated']

	def __init__(self, *args, **kwargs):
		super(VulnerabilityEvidenceSerializer, self).__init__(*args, **kwargs)
							
	def validate_request(self,data):
		return text_file_validator(data)

	def validate_response(self,data):
		return text_file_validator(data)

	def validate_log(self,data):
		return text_file_validator(data)		

	def validate_file(self,data):
		return image_file_validator(data)


class VulnerabilityRemediationSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,)
	# file = serializers.FileField(required=False)

	class Meta:
		model = VulnerabilityRemediation
		fields = ['id','description','file','vul','remediated_by','remediated_on','created_on','edited_on']
		read_only_fields = ['remediated_by','remediated_on','created_on','edited_on']

	def __init__(self, *args, **kwargs):
		super(VulnerabilityRemediationSerializer, self).__init__(*args, **kwargs)

	def validate_file(self,data):
		return image_file_validator(data)


class UpdateOpenVulnerabilitySerializer(serializers.Serializer):
	parser_classes = (JSONParser,)
	cwe = serializers.IntegerField(required=False)
	name = serializers.CharField(required=False)
	owasp = serializers.ChoiceField(required=False,choices=[(o,o) for o in settings.OWASP_TYPES])
	severity = serializers.ChoiceField(required=False,choices=[(0,'Info'),(1,'Low'),(2,'Medium'),(3,'High')])
	
	class Meta:
		fields = ['name','cwe','severity','owasp']


class OpenVulnerabilityRemediationSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,)
	file = serializers.FileField(required=False)

	class Meta:
		model = VulnerabilityRemediation
		fields = ['id','description','file','remediated_by','remediated_on','created_on','edited_on','vul']
		read_only_fields = ['remediated_by','remediated_on','created_on','edited_on','vul']

	def __init__(self, *args, **kwargs):
		super(OpenVulnerabilityRemediationSerializer, self).__init__(*args, **kwargs)

	def validate_file(self,data):
		return image_file_validator(data)

	def validate(self,data):
		if not data:
			raise serializers.ValidationError('Cannot submit a empty form')
		return data				


class VulnerabilityEvidenceRemediationSerializer(serializers.ModelSerializer):
	parser_classes = (MultiPartParser,)
	# file = serializers.FileField(required=False)

	class Meta:
		model = VulnerabilityEvidenceRemediation
		fields = ['id','description','file','evid','remediated_by','remediated_on','remediation_type','created_on','edited_on']
		read_only_fields = ['remediated_by','remediated_on','created_on','edited_on']	

	def __init__(self, *args, **kwargs):
		super(VulnerabilityEvidenceRemediationSerializer, self).__init__(*args, **kwargs)

	def validate_file(self,data):
		return image_file_validator(data)																								




			




		