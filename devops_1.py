#Imports for the code to work
import time
import boto3
import webbrowser
import json
import random
import string
import requests
import subprocess
import logging

#Logging Code

logging.basicConfig(
	filename='awsLoggingScript.log',
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

#Start of EC2 Variable Code-----------------------------------------------------------------------------------------


print ('Creating EC2 variables')
logging.info('Creating EC2 variables')
#Code to create an ec2 instance
ec2=boto3.resource('ec2')
#Adding a security group variabe for the instance
security_group_id=['sg-04ea941b7b65ea50c']
#Adding a Key Pair variable for the instance
key_pair='key_pair'
#Adding tags variable to name the instance
tags = [{'Key':'Name','Value':'Web server'}]
#This creates a user data variable that downloads apache web server, starts the server, and displays the following
#Line _ & _ display the instance id on the webpage
#Line _ & _ display what type of instance is being used
#Line _ & _ display where the instance is being hosted
user_data="""#!/bin/bash
yum install httpd -y
systemctl enable httpd
systemctl start httpd
echo '<html>' > index.html
echo 'Instance ID: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/instance-id >> index.html
echo '</br>' >> index.html
echo 'Instance Type: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/instance-type >> index.html
echo '</br>' >> index.html
echo 'Availability Zone: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html
echo '</br>' >> index.html
cp index.html /var/www/html/index.html
"""


#Start of EC2 Creation Code-----------------------------------------------------------------------------------------


print('Creating EC2 instance')
logging.info('Creating EC2 instance')
#Function to add the details to the instance during creation
try:
	new_instances=ec2.create_instances(
		#Assigning a machine image
		ImageId='ami-03eb6185d756497f8',
		#Dictating the aount of instances launched
		MinCount=1,
		MaxCount=1,
		#Assigning the instance type
		InstanceType='t2.nano',
		#Choosing a key pair
		KeyName=key_pair,
		#Applying the security rules
		SecurityGroupIds=security_group_id,
		#Using the tags variable
		TagSpecifications=[{'ResourceType':'instance','Tags':tags}],
		#Using the user data variable above
		UserData=user_data
)
except:
	print('An error occurred making this EC2 instance')
else:
	print(f'Created new instance {new_instances[0].id}')

#Making the script wait for the instance to launch before continuing
new_instances[0].wait_until_running()
#Reloading the instance
new_instances[0].reload()
#Creating a variable to store the ip of the instance
public_ip = new_instances[0].public_ip_address
print (f"Instance {new_instances[0].id} Running at {public_ip}")
logging.info(f"Instance {new_instances[0].id} Running at {public_ip}")

#Start of S3 Bucket Creation Code-----------------------------------------------------------------------------------


print('Creating S3 variables')
logging.info('Creating S3 cariables')
#Code to make S3 bucket
s3 = boto3.resource('s3')
#Code to create the name of the S3 instance which consists of 6 random letters and numbers then my name
characters = string.ascii_lowercase + string.digits
random_string = ''.join(random.choice(characters) for _ in range(6))
bucket_name=f'{random_string}-dkeane'
print (f'Creating new S3 bucket named {bucket_name}')
logging.info(f'Creating new S3 bucket named {bucket_name}')
try:
	#Launching the bucket
	s3.create_bucket(Bucket=bucket_name)
except:
	print('An error occured making this S3 Bucket') 

	
#Start of S3 Bucket Configuration and File Upload-------------------------------------------------------------------


#Deleting the access blocks on the bucket to allow public access
print('Applying new access policy and static website configuration')
logging.info('Applying new access policy and static website configuration')
s3client = boto3.client('s3')
s3client.delete_public_access_block(Bucket=bucket_name)
#Creating content type variables to stop bucket files being downloaded when trying to launch the website
content_html= 'text/html'
content_image= 'image/jpeg'
print('Uploading files to S3 bucket')
logging.info('Uploading files to S3 bucket')
try:
	#Uploading the index.html file to be displayed in the browser
	s3.Object(bucket_name, 'index.html').put(Body=open('index.html', 'rb'), ContentType=content_html)
	#Downloading Logo.jpg image then uploading the image to the S3 bucket
	logo_image=requests.get('http://devops.witdemo.net/logo.jpg')
	s3.Object(bucket_name, 'logo.jpg').put(Body=logo_image.content, ContentType=content_image)
except:
	print('Failed to upload files to the S3 bucket')
else:
	print('Upload Successful')
#Applying a static website configuration to the bucket
website_configuration = {
    'ErrorDocument': {'Key': 'error.html'},
    'IndexDocument': {'Suffix': 'index.html'}
}
bucket_website = s3.BucketWebsite(bucket_name)
responce=bucket_website.put(WebsiteConfiguration=website_configuration)
#Creating a new bucket policy variable
bucket_policy = {
    "Version": "2012-10-17",
    "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
	}]
}
#Applying the new bucket policy
bucket_policy_json = json.dumps(bucket_policy)
bucket = s3.Bucket(bucket_name)
bucket.Policy().put(Policy=bucket_policy_json)


#Start of Webpage Launch Code---------------------------------------------------------------------------------------


print('Pausing for 25 secs to allow apache install to finish')
logging.info('Pausing for 25 secs to allow apache install to finish')
#Pausing the script for 25 secs to allow apache to install
time.sleep(25)
print ('Done Waiting, Opening EC2 and S3 websites')
logging.info('Done Waiting, Opening EC2 and S3 websites')
try:
	#Opening the web server in the browser
	webbrowser.open_new_tab(f'http://{public_ip}')
except:
	print('Could not open EC2 website')
try:
	#Opening the static website in the browser
	webbrowser.open_new_tab(f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com')
except:
	print('Could not open S3 website')
#Takes the URLs of both the websites and puts them in a text file called dkeane-websites
filename='dkeane-websites.txt'
with open(filename, 'w') as file:
	file.write(f'http://{public_ip}\n')
	file.write(f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com')
print(f'Website URLs saved to text file {filename}')
logging.info(f'Website URLs saved to text file {filename}')

#monitoring.sh Code---------------------------------------------------------------------------------------

print("Beginning monitoring installation")
subprocess.run("chmod 400 key_pair.pem", shell=True)
secure_copy_command = (f'scp -i key_pair.pem -o StrictHostKeyChecking=no monitoring.sh ec2-user@{new_instances[0].public_ip_address}')
subprocess.run(secure_copy_command, shell=True)
print("Copy command successful. Waiting...")
time.sleep(50)
print("Waiting done, beginning ssh command")
#ssh_command = (f'ssh -o StrictHostKeyChecking=no -i key_pair.pem ec2-user@{new_instances[0].public_ip_address} " chmod 700 monitoring.sh"')
#subprocess.run(ssh_command, shell=True)
subprocess.run('ssh -i key_pair.pem -o StrictHostKeyChecking=no ec2-user@' + str(new_instances[0].public_ip_address) + " 'chmod 700 monitoring.sh'", shell=True)

#script_call_command = (f'ssh -o StrictHostKeyChecking=no -i key_pair.pem ec2-user@{new_instances[0].public_ip_address} " ./monitoring.sh"')
#subprocess.run(script_call_command, shell=True)
print("Command successful, attempting to launch script")
subprocess.run("ssh -i key_pair.pem -o StrictHostKeyChecking=no ec2-user@" + str(new_instances[0].public_ip_address) + " ' ./monitoring.sh'", shell=True)
print("Script running successfully")

#Citation
#For this assignment I didnt directly use anyone elses code but did get help and inspiration from the following
#StackOverflow
#Lab Notes
#AWS Documentation
