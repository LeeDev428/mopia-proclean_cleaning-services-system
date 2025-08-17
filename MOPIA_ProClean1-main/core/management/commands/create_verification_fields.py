from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Adds email verification fields to UserProfile table'

    def handle(self, *args, **options):
        self.stdout.write('Adding email verification fields to UserProfile...')
        
        try:
            with connection.cursor() as cursor:
                # Check if fields already exist
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'core_userprofile' AND column_name = 'is_email_verified'
                    )
                """)
                field_exists = cursor.fetchone()[0]
                
                if not field_exists:
                    # Add is_email_verified field with default False
                    cursor.execute("""
                        ALTER TABLE core_userprofile 
                        ADD COLUMN is_email_verified BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                    
                    # Add email_verification_token field
                    cursor.execute("""
                        ALTER TABLE core_userprofile 
                        ADD COLUMN email_verification_token VARCHAR(100) NULL
                    """)
                    
                    # Add token_expiry field
                    cursor.execute("""
                        ALTER TABLE core_userprofile 
                        ADD COLUMN token_expiry TIMESTAMP WITH TIME ZONE NULL
                    """)
                    
                    self.stdout.write(self.style.SUCCESS('✅ Successfully added email verification fields'))
                else:
                    self.stdout.write(self.style.SUCCESS('✅ Email verification fields already exist'))
                    
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error adding fields: {str(e)}'))
