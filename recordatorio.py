import boto3
import json
from os import environ
import smtplib
from email.message import EmailMessage

def lambda_handler(event, context):
    
    #Obtiene el recurso de los servicios
    sns = boto3.client('sns')
    ssm = boto3.client('ssm')
    secret = boto3.client('secretsmanager')
        
    #Obtiene contraseña de correo desde Secrets Manager
    email_password = json.loads(secret.get_secret_value(SecretId='password')['SecretString'])['password']

    #Obtiene saldo y dias desde Parameter Store y le da formato ($) al saldo
    dias = ssm.get_parameter(Name='dias')['Parameter']['Value']
    saldo = ssm.get_parameter(Name='saldo')['Parameter']['Value']
    currency = "${:,.2f} MXN".format(float(saldo))
    
    #Función para mandar mensaje por correo
    def mandar_correo():  

        # create an email message object
        message = EmailMessage()
              
        # configure email headers
        message['Subject'] = environ['email_subject']
        message['From'] = environ['sender_email_address']
        message['To'] = environ['receiver_email_address']
              
        # set email body text
        message.set_content(environ['mensaje_correo1'] + str(int(dias)) + environ['mensaje_correo2'] + currency)

              
        # set smtp server and port
        server = smtplib.SMTP(environ['email_smtp'], environ['smtp_port'])
        # identify this client to the SMTP server
        server.ehlo()
        # secure the SMTP connection
        server.starttls()
              
        # login to email account
        server.login(environ['sender_email_address'], email_password)
        # send email
        server.send_message(message)
        # close connection to server
        server.quit()
    
    #Actualiza saldo en Parameter Store
    def actualizar_saldo():
        saldonuevo = ssm.put_parameter(
        Name='saldo',
        Description='saldo',
        Value=str(int(saldo)+int(environ['recargo'])),
        Type='String',
        Overwrite=True
        )
        
    #Actualiza días en Parameter Store
    def actualizar_dias():
        diasnuevo = ssm.put_parameter(
        Name='dias',
        Description='dias',
        Value=str(int(dias)+1),
        Type='String',
        Overwrite=True
        )
        
    #Función para mandar mensajes por SMS
    def mandar_mensajes():
        
        #Mensaje a enviar renta vencida
        mensaje_sms_vencida = environ['mensaje_sms1'] + str(int(dias)) + environ['mensaje_sms2'] + currency
        
        #Decide a quién mandarle mensajes con base en el número de días de atraso
        #Decide qué mensaje mandar y por qué medio (sms y/o correo) con base en el número de días de atraso
        #Obtiene números de teléfono y mensajes de las variables de ambiente
        #Actualiza saldo en el caso de la renta vencida
        if int(dias) >= 7:
            sns.publish(PhoneNumber=environ['number'], Message=mensaje_sms_vencida)
            sns.publish(PhoneNumber=environ['altnumber'], Message=mensaje_sms_vencida)
            sns.publish(PhoneNumber=environ['yo'], Message=mensaje_sms_vencida)
            mandar_correo()
            actualizar_saldo()
            #print(mensaje_sms_vencida)
        elif int(dias) >= 1:
            sns.publish(PhoneNumber=environ['number'], Message=mensaje_sms_vencida)
            #sns.publish(PhoneNumber=environ['yo'], Message=mensaje_sms_vencida)
            actualizar_saldo()
            #print(mensaje_sms_vencida)
        elif int(dias) == 0:
            sns.publish(PhoneNumber=environ['number'], Message=environ['mensaje_sms_hoy'])
            #print(environ['mensaje_sms_hoy'])
        elif int(dias) == -1:
            sns.publish(PhoneNumber=environ['number'], Message=environ['mensaje_sms_manana'])
            #print(environ['mensaje_sms_manana'])
        else:
            sns.publish(PhoneNumber=environ['number'], Message=environ['mensaje_sms_tres_dias'])
            #print(environ['mensaje_sms_tres_dias'])
    
    #Ejecuta función para mandar recordatorio por SMS
    mandar_mensajes()
    
    #Ejecuta función para actualizar días
    actualizar_dias()