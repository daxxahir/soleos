app_name = "soleos"
app_title = "Soleos"
app_publisher = "Soleos"
app_description = "Soleos App"
app_email = "admin@soleosenergy.com"
app_license = "mit"

# Migration / Setup Hooks
after_migrate = ["soleos.setup_crm.setup_bigin_pipeline"]
after_install = ["soleos.setup_crm.setup_bigin_pipeline"]
