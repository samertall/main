"""Fictional seeded data. NEVER use these addresses for real delivery."""
DEMO_CONTACTS = [
    {"id":"maria","name":"Maria Ahmed","initials":"MA","role":"Parent / Grade 2","child":"Leila A.","email":"maria@example.org","phone":"+12025550101","preferred_channel":"sms","consent_email":True,"consent_sms":True,"status":"active","segment":"Grade 2 families"},
    {"id":"james","name":"James Reed","initials":"JR","role":"Parent / Grade 4","child":"Noah R.","email":"james@example.org","phone":"+12025550102","preferred_channel":"email","consent_email":True,"consent_sms":False,"status":"active","segment":"Grade 4 families"},
    {"id":"noura","name":"Noura Haddad","initials":"NH","role":"Parent / Grade 1","child":"Adam H.","email":"noura@example.org","phone":"+12025550103","preferred_channel":"sms","consent_email":True,"consent_sms":True,"status":"active","segment":"Grade 1 families"},
    {"id":"oliver","name":"Oliver Chen","initials":"OC","role":"Parent / Grade 3","child":"Maya C.","email":"oliver@example.org","phone":"+12025550104","preferred_channel":"email","consent_email":True,"consent_sms":False,"status":"active","segment":"Grade 3 families"},
]
SEED_MESSAGES = {
    "maria": [
        ("outbound", "sms", "Hello Maria! The Autumn Learning Day is this Friday at 10:00 AM. Reply here with any questions.", "announcement"),
        ("inbound", "sms", "Is there a vegetarian lunch option for Leila?", "resources"),
        ("outbound", "sms", "Thanks for asking! The event meal arrangements have not been confirmed in the school guide. I have flagged this for the office to verify before we give you an answer.", "handoff"),
    ],
    "james": [
        ("outbound", "email", "Hello James! Parent conferences are held on Thursdays, 3:00-5:00 PM. Reply to request a time.", "announcement"),
        ("inbound", "email", "Could I speak with Noah's teacher next week?", "scheduling"),
        ("outbound", "email", "Absolutely. I can pass your request to the school office. What day works best? A staff member will confirm the appointment.", "scheduling"),
    ],
    "noura": [
        ("outbound", "sms", "Welcome, Noura. You can reply in this thread for general school support.", "announcement"),
        ("inbound", "sms", "I need the homework resources", "resources"),
        ("outbound", "sms", "The family resource portal is https://example.org/resources (demo link). Would you like this information by email instead?", "resources"),
    ],
    "oliver": [
        ("outbound", "email", "Hello Oliver! Welcome to ParentBridge. We're here to make communication easier.", "announcement"),
    ],
}
