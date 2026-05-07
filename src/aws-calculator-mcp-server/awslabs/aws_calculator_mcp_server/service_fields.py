# Scraped field names from calculator.aws (May 2026) - 159 services
SERVICE_FIELDS = {
    "AWS Amplify": {
        "description": "Number of build minutes, Data stored per month, Data served per month, Number of SSR requests",
        "fields": {
            "number_of_build_minutes": "Number of build minutes",
            "data_stored_per_month": "Data stored per month",
            "data_served_per_month": "Data served per month",
            "number_of_ssr_requests": "Number of SSR requests",
            "duration_of_each_request_in_ms": "Duration of each request (in ms)",
        },
    },
    "AWS App Runner": {
        "description": "Concurrency, Minimum provisioned container instances, Peak traffic hours, Number of requests during peak traffic (requests/second)",
        "fields": {
            "concurrency": "Concurrency",
            "minimum_provisioned_container_instances": "Minimum provisioned container instances",
            "peak_traffic_hours": "Peak traffic hours",
            "number_of_requests_during_peak_traffic_requestssec": "Number of requests during peak traffic (requests/second)",
            "number_of_requests_during_offpeak_traffic_requests": "Number of requests during off-peak traffic (requests/second)",
        },
    },
    "AWS AppSync": {
        "description": "Number of API Requests, Enter Amount",
        "fields": {
            "number_of_api_requests": "Number of API Requests",
            "enter_amount": "Enter Amount",
        },
    },
    "AWS Application Migration Service": {
        "description": "Number of server/s, Number of hour/s per server",
        "fields": {
            "number_of_servers": "Number of server/s",
            "number_of_hours_per_server": "Number of hour/s per server",
        },
    },
    "AWS Audit Manager": {
        "description": "Number of accounts, Number of resources per account, Number of configuration snapshots (API calls), Number of configuration changes/user activity logs (Cloudtrail)",
        "fields": {
            "number_of_accounts": "Number of accounts",
            "number_of_resources_per_account": "Number of resources per account",
            "number_of_configuration_snapshots_api_calls": "Number of configuration snapshots (API calls)",
            "number_of_configuration_changesuser_activity_logs_": "Number of configuration changes/user activity logs (Cloudtrail)",
            "number_of_compliance_checks_security_hub_config": "Number of compliance checks (Security Hub, Config)",
        },
    },
    "AWS B2B Data Interchange": {
        "description": "Number of partnerships, Number of transformation steps per month",
        "fields": {
            "number_of_partnerships": "Number of partnerships",
            "number_of_transformation_steps_per_month": "Number of transformation steps per month",
        },
    },
    "AWS Backup": {
        "description": "Amount of primary data (GB), daily change %, retention periods (days/weeks/months)",
        "fields": {
            "primary_data_gb": "Amount of primary data to be backed up",
            "daily_change_pct": "Estimated daily change of primary data",
            "daily_warm_retention": "Daily backups warm retention period",
            "weekly_warm_retention": "Weekly backups warm retention period",
            "monthly_warm_retention": "Monthly backups warm retention period",
        },
    },
    "AWS Certificate Manager": {
        "description": "Number of fully qualified domain names (FQDNs), Number of wildcard domain names, Number of API calls",
        "fields": {
            "number_of_fully_qualified_domain_names_fqdns": "Number of fully qualified domain names (FQDNs)",
            "number_of_wildcard_domain_names": "Number of wildcard domain names",
            "number_of_api_calls": "Number of API calls",
        },
    },
    "AWS Cloud Map": {
        "description": "AWS Cloud Map - no additional configuration",
        "fields": {
        },
    },
    "AWS CloudFormation": {
        "description": "Number of third-party extensions managed, Total number of operations per extension",
        "fields": {
            "number_of_thirdparty_extensions_managed": "Number of third-party extensions managed",
            "total_number_of_operations_per_extension": "Total number of operations per extension",
        },
    },
    "AWS CloudHSM": {
        "description": "Total number of hsm1.medium HSMs, Total number of hsm2m.medium HSMs",
        "fields": {
            "total_number_of_hsm1medium_hsms": "Total number of hsm1.medium HSMs",
            "total_number_of_hsm2mmedium_hsms": "Total number of hsm2m.medium HSMs",
        },
    },
    "AWS CloudTrail": {
        "description": "Number of management events, Management event trails, Read management events, Read management trails",
        "fields": {
            "number_of_management_events": "Number of management events",
            "management_event_trails": "Management event trails",
            "read_management_events": "Read management events",
            "read_management_trails": "Read management trails",
            "s3_operations": "S3 operations",
            "s3_trails": "S3 trails",
            "lambda_data_events": "Lambda data events",
            "lambda_trails": "Lambda trails",
            "number_of_network_activity_events": "Number of network activity events",
            "network_activity_event_trails": "Network activity event trails",
            "total_number_of_management_api_calls_both_read_and": "Total number of management API calls (both read and write) to be analyzed for unusual activity",
            "number_of_trails_andor_event_data_stores_where_ins": "Number of trails and/or event data stores where Insights events are enabled",
            "data_ingested_cloudtrail": "Data ingested - CloudTrail",
            "data_ingested_7_year_retention": "Data ingested - 7 year retention",
            "data_scanned_using_queries": "Data scanned using queries",
        },
    },
    "AWS CodeArtifact": {
        "description": "Size of artifacts stored, Number of API requests, Enter Amount",
        "fields": {
            "size_of_artifacts_stored": "Size of artifacts stored",
            "number_of_api_requests": "Number of API requests",
            "enter_amount": "Enter Amount",
        },
    },
    "AWS CodeBuild": {
        "description": "Number of builds in a month, Average build duration (minutes)",
        "fields": {
            "number_of_builds_in_a_month": "Number of builds in a month",
            "average_build_duration_minutes": "Average build duration (minutes)",
            "operating_system": "_autosuggest:Select an instance",
        },
    },
    "AWS CodeDeploy": {
        "description": "Number of on-premise instances, Number of deployments",
        "fields": {
            "number_of_onpremise_instances": "Number of on-premise instances",
            "number_of_deployments": "Number of deployments",
        },
    },
    "AWS CodePipeline": {
        "description": "Number of active pipelines of type V1 used per account per month, Number of action execution minutes used in pipeline of type V2 per account per month",
        "fields": {
            "number_of_active_pipelines_of_type_v1_used_per_acc": "Number of active pipelines of type V1 used per account per month",
            "number_of_action_execution_minutes_used_in_pipelin": "Number of action execution minutes used in pipeline of type V2 per account per month",
        },
    },
    "AWS Config": {
        "description": "Number of Continuous Configuration items recorded, Number of Periodic Configuration items recorded, Number of Config rule evaluations, Number of Conformance pack evaluations",
        "fields": {
            "number_of_continuous_configuration_items_recorded": "Number of Continuous Configuration items recorded",
            "number_of_periodic_configuration_items_recorded": "Number of Periodic Configuration items recorded",
            "number_of_config_rule_evaluations": "Number of Config rule evaluations",
            "number_of_conformance_pack_evaluations": "Number of Conformance pack evaluations",
        },
    },
    "AWS Data Transfer": {
        "description": "Enter Amount",
        "fields": {
            "enter_amount": "Enter Amount",
        },
    },
    "AWS DataSync": {
        "description": "Total data copied by AWS DataSync per month",
        "fields": {
            "total_data_copied_by_aws_datasync_per_month": "Total data copied by AWS DataSync per month",
        },
    },
    "AWS Database Migration Service": {
        "description": "Number of instances, Storage amount (multiple AZ)",
        "fields": {
            "number_of_instances": "Number of instances",
            "instance_type": "_autosuggest:Select an instance",
            "storage_amount_multiple_az": "Storage amount (multiple AZ)",
        },
    },
    "AWS Deadline Cloud": {
        "description": "Number of Instance, Monthly utilization, Storage per worker, Utilization (On-Demand only)",
        "fields": {
            "number_of_instance": "Number of Instance",
            "instance_type": "_autosuggest:Select an instance",
            "monthly_utilization": "Monthly utilization",
            "storage_per_worker": "Storage per worker",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
        },
    },
    "AWS Direct Connect": {
        "description": "Number of ports, Hours used, Data transfer out, Data transfer in (free)",
        "fields": {
            "number_of_ports": "Number of ports",
            "hours_used": "Hours used",
            "data_transfer_out": "Data transfer out",
            "data_transfer_in_free": "Data transfer in (free)",
        },
    },
    "AWS Directory Service": {
        "description": "Total number of directories, Number of total additional domain controllers, Number of directories to be shared, Number of additional accounts to which each directory is shared",
        "fields": {
            "total_number_of_directories": "Total number of directories",
            "number_of_total_additional_domain_controllers": "Number of total additional domain controllers",
            "number_of_directories_to_be_shared": "Number of directories to be shared",
            "number_of_additional_accounts_to_which_each_direct": "Number of additional accounts to which each directory is shared",
        },
    },
    "AWS Elastic Disaster Recovery": {
        "description": "Number of source servers replicated per month, Number of disks, Storage on all disks and all servers, Number of days selected for EBS snapshot retention period",
        "fields": {
            "number_of_source_servers_replicated_per_month": "Number of source servers replicated per month",
            "number_of_disks": "Number of disks",
            "storage_on_all_disks_and_all_servers": "Storage on all disks and all servers",
            "number_of_days_selected_for_ebs_snapshot_retention": "Number of days selected for EBS snapshot retention period",
        },
    },
    "AWS Elemental Media Tailor": {
        "description": "Basic tier channel hours per month, Standard tier channel hours per month",
        "fields": {
            "basic_tier_channel_hours_per_month": "Basic tier channel hours per month",
            "standard_tier_channel_hours_per_month": "Standard tier channel hours per month",
        },
    },
    "AWS Elemental MediaConnect": {
        "description": "Number of running flows, Flow utilization, Number of outputs per flow, Bitrate (Mbit per second)",
        "fields": {
            "number_of_running_flows": "Number of running flows",
            "flow_utilization": "Flow utilization",
            "number_of_outputs_per_flow": "Number of outputs per flow",
            "bitrate_mbit_per_second": "Bitrate (Mbit per second)",
            "running_flow_utilization": "Running flow utilization",
            "number_of_running_outputs": "Number of running outputs",
            "running_output_utilization": "Running output utilization",
            "enter_amount": "Enter Amount",
        },
    },
    "AWS Elemental MediaConvert": {
        "description": "Output basic usage",
        "fields": {
            "output_basic_usage": "Output basic usage",
        },
    },
    "AWS Elemental MediaLive": {
        "description": "Number of inputs, Active hours (On Demand), Number of outputs",
        "fields": {
            "number_of_inputs": "Number of inputs",
            "active_hours_on_demand": "Active hours (On Demand)",
            "number_of_outputs": "Number of outputs",
        },
    },
    "AWS Elemental MediaPackage": {
        "description": "Number of inputs per channel, Total duration of live streams per month, Ingest bitrate per input (Mbit per second), Average Number of viewers per hour",
        "fields": {
            "number_of_inputs_per_channel": "Number of inputs per channel",
            "total_duration_of_live_streams_per_month": "Total duration of live streams per month",
            "ingest_bitrate_per_input_mbit_per_second": "Ingest bitrate per input (Mbit per second)",
            "average_number_of_viewers_per_hour": "Average Number of viewers per hour",
            "average_bitrate_per_viewer_mbit_per_second": "Average bitrate per viewer (Mbit per second)",
            "cachehit_ratio_enter_cachehit_ratio_as_a_pecentage": "Cache/hit ratio Enter cache/hit ratio as a pecentage",
            "hours_of_vod_content_watched": "Hours of VOD content watched",
            "average_bitrate_mbit_per_second": "Average bitrate (Mbit per second)",
        },
    },
    "AWS Entity Resolution": {
        "description": "Number of Records",
        "fields": {
            "number_of_records": "Number of Records",
        },
    },
    "AWS Fargate": {
        "description": "Number of tasks or pods, Average duration, Amount of memory allocated, Amount of ephemeral storage allocated for Amazon ECS",
        "fields": {
            "number_of_tasks_or_pods": "Number of tasks or pods",
            "average_duration": "Average duration",
            "amount_of_memory_allocated": "Amount of memory allocated",
            "amount_of_ephemeral_storage_allocated_for_amazon_e": "Amount of ephemeral storage allocated for Amazon ECS",
        },
    },
    "AWS Fault Injection Service (FIS)": {
        "description": "Experiments per Month, Average action-minutes per experiment, Average count of target accounts per experiment, % of Experiments per Month with experiment report Enter %",
        "fields": {
            "experiments_per_month": "Experiments per Month",
            "average_actionminutes_per_experiment": "Average action-minutes per experiment",
            "average_count_of_target_accounts_per_experiment": "Average count of target accounts per experiment",
            "of_experiments_per_month_with_experiment_report_en": "% of Experiments per Month with experiment report Enter %",
        },
    },
    "AWS Firewall Manager": {
        "description": "Number of protection policy, Number of aws account, Number of Configuration items recorded, Number of Config rule evaluations",
        "fields": {
            "number_of_protection_policy": "Number of protection policy",
            "number_of_aws_account": "Number of aws account",
            "number_of_configuration_items_recorded": "Number of Configuration items recorded",
            "number_of_config_rule_evaluations": "Number of Config rule evaluations",
            "number_of_aws_network_firewall_endpoints": "Number of AWS Network Firewall endpoints",
            "usage_per_endpoint": "Usage per endpoint",
            "data_processed_per_month": "Data processed per month",
            "number_of_web_access_control_lists_web_acls_utiliz": "Number of Web Access Control Lists (Web ACLs) utilized",
            "number_of_rules_added_per_web_acl": "Number of Rules added per Web ACL",
            "number_of_domains_stored": "Number of domains stored",
            "dns_queries": "DNS queries",
            "elastic_load_balancing_elb_usage": "Elastic Load Balancing (ELB) Usage",
            "elastic_ip_usage": "Elastic IP Usage",
            "number_of_security_groups": "Number of Security groups",
        },
    },
    "AWS Glue": {
        "description": "Number of DPUs for Apache Spark job, Duration for which Apache Spark ETL job  runs, Number of DPUs for Python Shell job, Number of DPUs for each provisioned interactive session",
        "fields": {
            "number_of_dpus_for_apache_spark_job": "Number of DPUs for Apache Spark job",
            "duration_for_which_apache_spark_etl_job_runs": "Duration for which Apache Spark ETL job  runs",
            "number_of_dpus_for_python_shell_job": "Number of DPUs for Python Shell job",
            "number_of_dpus_for_each_provisioned_interactive_se": "Number of DPUs for each provisioned interactive session",
        },
    },
    "AWS IAM Access Analyzer": {
        "description": "Number of accounts to monitor, Average roles per account, Average users per account, Number of analyzers per account",
        "fields": {
            "number_of_accounts_to_monitor": "Number of accounts to monitor",
            "average_roles_per_account": "Average roles per account",
            "average_users_per_account": "Average users per account",
            "number_of_analyzers_per_account": "Number of analyzers per account",
            "number_of_requests_to_checknonewaccess_api": "Number of requests to CheckNoNewAccess API",
            "number_of_requests_to_checkaccessnotgranted_api": "Number of requests to CheckAccessNotGranted API",
            "number_of_resources_to_monitor": "Number of resources to monitor",
        },
    },
    "AWS IoT Analytics": {
        "description": "Number of IoT devices (monthly), Data generation by each device, Number of data pipelines (monthly), Data queried per month",
        "fields": {
            "number_of_iot_devices_monthly": "Number of IoT devices (monthly)",
            "data_generation_by_each_device": "Data generation by each device",
            "number_of_data_pipelines_monthly": "Number of data pipelines (monthly)",
            "data_queried_per_month": "Data queried per month",
            "number_of_queries_monthly": "Number of queries (monthly)",
            "data_scanned_per_query": "Data scanned per query",
            "average_acu_execution_time": "Average ACU execution time",
        },
    },
    "AWS IoT Core": {
        "description": "Number of devices (MQTT)",
        "fields": {
            "number_of_devices_mqtt": "Number of devices (MQTT)",
        },
    },
    "AWS IoT Device Defender": {
        "description": "AWS IoT Device Defender - no additional configuration",
        "fields": {
        },
    },
    "AWS IoT Device Management": {
        "description": "AWS IoT Device Management - no additional configuration",
        "fields": {
        },
    },
    "AWS IoT Events": {
        "description": "Number of devices, Number of messages for a device including timer expiry messages, Number of event detector models per device, Average size of each message",
        "fields": {
            "number_of_devices": "Number of devices",
            "number_of_messages_for_a_device_including_timer_ex": "Number of messages for a device including timer expiry messages",
            "number_of_event_detector_models_per_device": "Number of event detector models per device",
            "average_size_of_each_message": "Average size of each message",
            "number_of_actions_triggered_per_message": "Number of actions triggered per message",
        },
    },
    "AWS IoT Greengrass": {
        "description": "Number of greengrass core devices, Activity Period in minutes per month, MQTT topics with cloud as source (optional), Number of client devices per greengrass core device (optional)",
        "fields": {
            "number_of_greengrass_core_devices": "Number of greengrass core devices",
            "activity_period_in_minutes_per_month": "Activity Period in minutes per month",
            "mqtt_topics_with_cloud_as_source_optional": "MQTT topics with cloud as source (optional)",
            "number_of_client_devices_per_greengrass_core_devic": "Number of client devices per greengrass core device (optional)",
        },
    },
    "AWS IoT SiteWise": {
        "description": "Number of daily measurements, Number of tags or sensors, Cloud data availablity, Buffer period",
        "fields": {
            "number_of_daily_measurements": "Number of daily measurements",
            "number_of_tags_or_sensors": "Number of tags or sensors",
            "cloud_data_availablity": "Cloud data availablity",
            "buffer_period": "Buffer period",
            "number_of_messages_in_response_to_egress_api_calls": "Number of messages in response to egress API calls",
            "total_computations_of_metrics_and_transforms": "Total computations of metrics and transforms",
            "volume_of_data_gb": "Volume of data (GB)",
            "count_of_monthly_active_users": "Count of monthly active users",
            "cost_of_egress_from_iot_sitewise_pricing_tool": "Cost of Egress from IoT Sitewise Pricing Tool",
        },
    },
    "AWS Key Management Service": {
        "description": "Number of customer managed Customer Master Keys (CMK), Number of symmetric requests, Number of asymmetric requests except RSA 2048, Number of asymmetric requests involving RSA 2048",
        "fields": {
            "number_of_customer_managed_customer_master_keys_cm": "Number of customer managed Customer Master Keys (CMK)",
            "number_of_symmetric_requests": "Number of symmetric requests",
            "number_of_asymmetric_requests_except_rsa_2048": "Number of asymmetric requests except RSA 2048",
            "number_of_asymmetric_requests_involving_rsa_2048": "Number of asymmetric requests involving RSA 2048",
            "number_of_ecc_generatedatakeypair_requests": "Number of ECC GenerateDataKeyPair requests",
            "number_of_rsa_generatedatakeypair_requests": "Number of RSA GenerateDataKeyPair requests",
        },
    },
    "AWS Lake Formation": {
        "description": "Data scanned, Storage usage in a month (in millions), Requests in a month (in millions), Number of tables",
        "fields": {
            "data_scanned": "Data scanned",
            "storage_usage_in_a_month_in_millions": "Storage usage in a month (in millions)",
            "requests_in_a_month_in_millions": "Requests in a month (in millions)",
            "number_of_tables": "Number of tables",
            "number_of_small_files_ingested_per_table_per_day": "Number of small files ingested per table per day",
            "size_of_small_files_less_than_64mb": "Size of small files (less than 64MB)",
        },
    },
    "AWS Lambda": {
        "description": "Number of requests, Duration of each request (in ms), Amount of memory allocated, Amount of ephemeral storage allocated",
        "fields": {
            "number_of_requests": "Number of requests",
            "duration_of_each_request_in_ms": "Duration of each request (in ms)",
            "amount_of_memory_allocated": "Amount of memory allocated",
            "amount_of_ephemeral_storage_allocated": "Amount of ephemeral storage allocated",
            "concurrency": "Concurrency",
            "duration_of_each_provisioned_request_in_ms": "Duration of each provisioned request (in ms)",
            "number_of_coldstarts_ie_snapstart_restores": "Number of cold-starts (i.e. SnapStart restores)",
        },
    },
    "AWS Mainframe Modernization": {
        "description": "Number of instances, Monthly utilization",
        "fields": {
            "number_of_instances": "Number of instances",
            "monthly_utilization": "Monthly utilization",
        },
    },
    "AWS Migration Hub Refactor Spaces": {
        "description": "Number of Environments, Number of Hours, API Requests",
        "fields": {
            "number_of_environments": "Number of Environments",
            "number_of_hours": "Number of Hours",
            "api_requests": "API Requests",
        },
    },
    "AWS Network Firewall": {
        "description": "Number of AWS Network Firewall endpoints, Monthly usage per endpoint, Advanced Inspection Monthly usage per endpoint, Number of Network Firewall secondary endpoints",
        "fields": {
            "number_of_aws_network_firewall_endpoints": "Number of AWS Network Firewall endpoints",
            "monthly_usage_per_endpoint": "Monthly usage per endpoint",
            "advanced_inspection_monthly_usage_per_endpoint": "Advanced Inspection Monthly usage per endpoint",
            "number_of_network_firewall_secondary_endpoints": "Number of Network Firewall secondary endpoints",
            "usage_per_secondary_endpoint": "Usage per secondary endpoint",
            "data_processed_per_month": "Data processed per month",
        },
    },
    "AWS PCS": {
        "description": "Number of PCS Clusters, Length of time cluster is running",
        "fields": {
            "number_of_pcs_clusters": "Number of PCS Clusters",
            "length_of_time_cluster_is_running": "Length of time cluster is running",
        },
    },
    "AWS Payment Cryptography": {
        "description": "Number of API requests, Number of active keys",
        "fields": {
            "number_of_api_requests": "Number of API requests",
            "number_of_active_keys": "Number of active keys",
        },
    },
    "AWS Private Certificate Authority": {
        "description": "Number of Private CAs, Number of general purpose mode private certificates issued, Number of certificates used with ACM-integrated services, Number of short lived certificate mode private certificates issued",
        "fields": {
            "number_of_private_cas": "Number of Private CAs",
            "number_of_general_purpose_mode_private_certificate": "Number of general purpose mode private certificates issued",
            "number_of_certificates_used_with_acmintegrated_ser": "Number of certificates used with ACM-integrated services",
            "number_of_short_lived_certificate_mode_private_cer": "Number of short lived certificate mode private certificates issued",
            "number_of_ocsp_responses_per_month": "Number of OCSP responses per Month",
            "number_of_ocsp_queries_per_hour": "Number of OCSP Queries per hour",
        },
    },
    "AWS Resilience Hub": {
        "description": "Number of applications assessed for resilience",
        "fields": {
            "number_of_applications_assessed_for_resilience": "Number of applications assessed for resilience",
        },
    },
    "AWS Secrets Manager": {
        "description": "Number of secrets, Average duration of each secret, Number of API calls",
        "fields": {
            "number_of_secrets": "Number of secrets",
            "average_duration_of_each_secret": "Average duration of each secret",
            "number_of_api_calls": "Number of API calls",
        },
    },
    "AWS Security Hub": {
        "description": "Number of Accounts, Number of Security Checks per Account, Number of Finding Ingested per Account, Number of Automation Rules",
        "fields": {
            "number_of_accounts": "Number of Accounts",
            "number_of_security_checks_per_account": "Number of Security Checks per Account",
            "number_of_finding_ingested_per_account": "Number of Finding Ingested per Account",
            "number_of_automation_rules": "Number of Automation Rules",
            "number_of_criteria_in_each_automation_rule": "Number of criteria in each automation rule",
        },
    },
    "AWS Service Catalog": {
        "description": "Number of API calls",
        "fields": {
            "number_of_api_calls": "Number of API calls",
        },
    },
    "AWS Shield": {
        "description": "Cloud Front Usage, Elastic Load Balancing (ELB) Usage, Elastic IP Usage, Global Accelerator Usage",
        "fields": {
            "cloud_front_usage": "Cloud Front Usage",
            "elastic_load_balancing_elb_usage": "Elastic Load Balancing (ELB) Usage",
            "elastic_ip_usage": "Elastic IP Usage",
            "global_accelerator_usage": "Global Accelerator Usage",
        },
    },
    "AWS SimSpace Weaver": {
        "description": "Number of instances, Usage",
        "fields": {
            "number_of_instances": "Number of instances",
            "instance_type": "_autosuggest:Select an instance",
            "usage": "Usage",
        },
    },
    "AWS Snowball": {
        "description": "Number of devices",
        "fields": {
            "number_of_devices": "Number of devices",
        },
    },
    "AWS Step Functions": {
        "description": "Workflow requests, State transitions per workflow",
        "fields": {
            "workflow_requests": "Workflow requests",
            "state_transitions_per_workflow": "State transitions per workflow",
        },
    },
    "AWS Storage Gateway": {
        "description": "Data written to AWS file storage by your gateway, Enter Amount",
        "fields": {
            "data_written_to_aws_file_storage_by_your_gateway": "Data written to AWS file storage by your gateway",
            "enter_amount": "Enter Amount",
        },
    },
    "AWS Systems Manager": {
        "description": "Standard parameters, Advanced parameters, Frequency of API interactions per parameter",
        "fields": {
            "standard_parameters": "Standard parameters",
            "advanced_parameters": "Advanced parameters",
            "frequency_of_api_interactions_per_parameter": "Frequency of API interactions per parameter",
        },
    },
    "AWS Transfer Family": {
        "description": "Total number of endpoints with AS2 enabled, Number of AS2 messages sent per month, Number of AS2 messages received per month",
        "fields": {
            "total_number_of_endpoints_with_as2_enabled": "Total number of endpoints with AS2 enabled",
            "number_of_as2_messages_sent_per_month": "Number of AS2 messages sent per month",
            "number_of_as2_messages_received_per_month": "Number of AS2 messages received per month",
        },
    },
    "AWS Web Application Firewall (WAF)": {
        "description": "Number of Web Access Control Lists (Web ACLs) utilized, Number of Rules added per Web ACL, Number of Rules inside each Rule Group, Number of web requests received across all web ACLs",
        "fields": {
            "number_of_web_access_control_lists_web_acls_utiliz": "Number of Web Access Control Lists (Web ACLs) utilized",
            "number_of_rules_added_per_web_acl": "Number of Rules added per Web ACL",
            "number_of_rules_inside_each_rule_group": "Number of Rules inside each Rule Group",
            "number_of_web_requests_received_across_all_web_acl": "Number of web requests received across all web ACLs",
        },
    },
    "AWS X-Ray": {
        "description": "Number of requests per month, Number of queries per month, Traces retrieved per query",
        "fields": {
            "number_of_requests_per_month": "Number of requests per month",
            "number_of_queries_per_month": "Number of queries per month",
            "traces_retrieved_per_query": "Traces retrieved per query",
        },
    },
    "Amazon API Gateway": {
        "description": "Requests, Average size of each request, Requests, Messages",
        "fields": {
            "requests": "Requests",
            "average_size_of_each_request": "Average size of each request",
            "requests_2": "Requests",
            "messages": "Messages",
            "average_message_size": "Average message size",
            "average_connection_rate": "Average connection rate",
        },
    },
    "Amazon AppFlow": {
        "description": "Number of flows, Volume of data per flow",
        "fields": {
            "number_of_flows": "Number of flows",
            "volume_of_data_per_flow": "Volume of data per flow",
        },
    },
    "Amazon Athena": {
        "description": "Total number of queries, Amount of data scanned per query, Number of DPUs, Length of time capacity is active",
        "fields": {
            "total_number_of_queries": "Total number of queries",
            "amount_of_data_scanned_per_query": "Amount of data scanned per query",
            "number_of_dpus": "Number of DPUs",
            "length_of_time_capacity_is_active": "Length of time capacity is active",
            "total_number_of_spark_sessions": "Total number of spark sessions",
            "code_execution_per_session": "Code execution per session",
        },
    },
    "Amazon Augmented AI": {
        "description": "Number of reviewed images per month with Amazon Rekognition and Amazon Augmented AI, Number of reviewed pages per month with Amazon Textract and Amazon Augmented AI, Number of reviewed objects per month with a Custom Model and Amazon Augmented AI",
        "fields": {
            "number_of_reviewed_images_per_month_with_amazon_re": "Number of reviewed images per month with Amazon Rekognition and Amazon Augmented AI",
            "number_of_reviewed_pages_per_month_with_amazon_tex": "Number of reviewed pages per month with Amazon Textract and Amazon Augmented AI",
            "number_of_reviewed_objects_per_month_with_a_custom": "Number of reviewed objects per month with a Custom Model and Amazon Augmented AI",
        },
    },
    "Amazon Aurora MySQL-Compatible": {
        "description": "Nodes, Utilization, Storage amount, Baseline IO rate",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization": "Utilization",
            "storage_amount": "Storage amount",
            "baseline_io_rate": "Baseline IO rate",
            "duration_of_peak_io_activity": "Duration of peak IO activity",
            "number_of_hours_running_on_amazon_rds_extended_sup": "Number of hours running on Amazon RDS Extended Support",
        },
    },
    "Amazon Aurora PostgreSQL-Compatible DB": {
        "description": "Quantity, Utilization, Storage amount, Baseline IO rate",
        "fields": {
            "quantity": "Quantity",
            "instance_type": "_autosuggest:Select an instance",
            "utilization": "Utilization",
            "storage_amount": "Storage amount",
            "baseline_io_rate": "Baseline IO rate",
            "duration_of_peak_io_activity": "Duration of peak IO activity",
            "number_of_hours_running_on_amazon_rds_extended_sup": "Number of hours running on Amazon RDS Extended Support",
        },
    },
    "Amazon Bedrock": {
        "description": "Average requests per minute, Hours per day at this rate, Average input tokens per request, Average output tokens per request",
        "fields": {
            "average_requests_per_minute": "Average requests per minute",
            "hours_per_day_at_this_rate": "Hours per day at this rate",
            "average_input_tokens_per_request": "Average input tokens per request",
            "average_output_tokens_per_request": "Average output tokens per request",
        },
    },
    "Amazon Bedrock AgentCore": {
        "description": "Number of agent sessions per month, Average Session Duration (seconds), Average vCPU excluding I/O wait time, Average Session Memory (in GB)",
        "fields": {
            "number_of_agent_sessions_per_month": "Number of agent sessions per month",
            "average_session_duration_seconds": "Average Session Duration (seconds)",
            "average_vcpu_excluding_io_wait_time": "Average vCPU excluding I/O wait time",
            "average_session_memory_in_gb": "Average Session Memory (in GB)",
        },
    },
    "Amazon CloudFront": {
        "description": "Free Plan, Pro Plan, Business Plan, Premium Plan",
        "fields": {
            "free_plan": "Free Plan",
            "pro_plan": "Pro Plan",
            "business_plan": "Business Plan",
            "premium_plan": "Premium Plan",
        },
    },
    "Amazon CloudWatch": {
        "description": "Number of Metrics (includes detailed and custom metrics), GetMetricData: Number of metrics requested, GetMetricWidgetImage: Number of metrics requested, Number of other API requests",
        "fields": {
            "number_of_metrics_includes_detailed_and_custom_met": "Number of Metrics (includes detailed and custom metrics)",
            "getmetricdata_number_of_metrics_requested": "GetMetricData: Number of metrics requested",
            "getmetricwidgetimage_number_of_metrics_requested": "GetMetricWidgetImage: Number of metrics requested",
            "number_of_other_api_requests": "Number of other API requests",
            "number_of_vcpus_monitored_by_database_insights": "Number of vCPUs monitored by Database Insights",
            "number_of_aurora_capacity_units_acus_monitored_by_": "Number of Aurora Capacity Units (ACUs) monitored by Database Insights",
        },
    },
    "Amazon CodeGuru Reviewer": {
        "description": "Total number of repositories, Average lines of code (LOC) per repository",
        "fields": {
            "total_number_of_repositories": "Total number of repositories",
            "average_lines_of_code_loc_per_repository": "Average lines of code (LOC) per repository",
        },
    },
    "Amazon Cognito": {
        "description": "Number of monthly active users (MAU), Number of monthly active users (MAU) who sign in through SAML or OIDC federation, Number of token requests, Number of app clients",
        "fields": {
            "number_of_monthly_active_users_mau": "Number of monthly active users (MAU)",
            "number_of_monthly_active_users_mau_who_sign_in_thr": "Number of monthly active users (MAU) who sign in through SAML or OIDC federation",
            "number_of_token_requests": "Number of token requests",
            "number_of_app_clients": "Number of app clients",
        },
    },
    "Amazon Comprehend": {
        "description": "Number of documents asynchronous, Average characters in a document asynchronous",
        "fields": {
            "number_of_documents_asynchronous": "Number of documents asynchronous",
            "average_characters_in_a_document_asynchronous": "Average characters in a document asynchronous",
        },
    },
    "Amazon Comprehend Medical": {
        "description": "Number of text (utf-8) documents (NERe), Average characters in a document (NERe)",
        "fields": {
            "number_of_text_utf8_documents_nere": "Number of text (utf-8) documents (NERe)",
            "average_characters_in_a_document_nere": "Average characters in a document (NERe)",
        },
    },
    "Amazon Data firehose": {
        "description": "Number of records for data ingestion, Record size",
        "fields": {
            "number_of_records_for_data_ingestion": "Number of records for data ingestion",
            "record_size": "Record size",
        },
    },
    "Amazon Detective": {
        "description": "Data ingested from AWS CloudTrail, Amazon VPC Flow Logs, Amazon GuardDuty (per account, per region)",
        "fields": {
            "data_ingested_from_aws_cloudtrail_amazon_vpc_flow_": "Data ingested from AWS CloudTrail, Amazon VPC Flow Logs, Amazon GuardDuty (per account, per region)",
        },
    },
    "Amazon DocumentDB (with MongoDB compatibility)": {
        "description": "Quantity, Server utilization",
        "fields": {
            "quantity": "Quantity",
            "instance_type": "_autosuggest:Select an instance",
            "server_utilization": "Server utilization",
        },
    },
    "Amazon DynamoDB": {
        "description": "Average item size (all attributes), Percentage of Non-transactional writes Enter the percentage, Baseline write rate, Peak write rate",
        "fields": {
            "average_item_size_all_attributes": "Average item size (all attributes)",
            "percentage_of_nontransactional_writes_enter_the_pe": "Percentage of Non-transactional writes Enter the percentage",
            "baseline_write_rate": "Baseline write rate",
            "peak_write_rate": "Peak write rate",
            "duration_of_peak_write_activity": "Duration of peak write activity",
            "baseline_read_rate": "Baseline read rate",
            "peak_read_rate": "Peak read rate",
        },
    },
    "Amazon EC2": {
        "description": "Number of instances, instance type (autosuggest), pricing model (On-Demand/Savings Plans/Reserved/Spot), EBS storage (GB)",
        "fields": {
            "number_of_instances": "Number of instances",
            "instance_type": "_autosuggest:Search instance type",
            "pricing_model": "_radio",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon EKS": {
        "description": "Number of EKS Clusters",
        "fields": {
            "number_of_eks_clusters": "Number of EKS Clusters",
        },
    },
    "Amazon EMR": {
        "description": "Number of master EMR nodes, Utilization, Number of core EMR nodes",
        "fields": {
            "number_of_master_emr_nodes": "Number of master EMR nodes",
            "utilization": "Utilization",
            "number_of_core_emr_nodes": "Number of core EMR nodes",
        },
    },
    "Amazon ElastiCache": {
        "description": "Nodes, Utilization (On-Demand only)",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
        },
    },
    "Amazon Elastic Block Store (EBS)": {
        "description": "Number of volumes, Average duration of volume, Storage amount per volume, Amount changed per snapshot",
        "fields": {
            "number_of_volumes": "Number of volumes",
            "average_duration_of_volume": "Average duration of volume",
            "storage_amount_per_volume": "Storage amount per volume",
            "amount_changed_per_snapshot": "Amount changed per snapshot",
            "number_of_snapshots_to_restore": "Number of snapshots to restore",
            "number_of_getsnapshotblock_api_requests": "Number of GetSnapshotBlock API requests",
        },
    },
    "Amazon Elastic Container Registry": {
        "description": "Amount of data stored, Enter Amount",
        "fields": {
            "amount_of_data_stored": "Amount of data stored",
            "enter_amount": "Enter Amount",
        },
    },
    "Amazon Elastic File System (EFS)": {
        "description": "Desired Storage Capacity, Infrequent Access Tiering, Infrequent Access Read, Archive Access Tiering",
        "fields": {
            "desired_storage_capacity": "Desired Storage Capacity",
            "infrequent_access_tiering": "Infrequent Access Tiering",
            "infrequent_access_read": "Infrequent Access Read",
            "archive_access_tiering": "Archive Access Tiering",
            "archive_access_read": "Archive Access Read",
            "read_data_transferred": "Read Data Transferred",
            "write_data_transferred": "Write Data Transferred",
        },
    },
    "Amazon Elastic Graphics": {
        "description": "Number of nodes, Utilization (On-Demand only)",
        "fields": {
            "number_of_nodes": "Number of nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
        },
    },
    "Amazon Elastic VMware Service": {
        "description": "Number of Instances",
        "fields": {
            "number_of_instances": "Number of Instances",
        },
    },
    "Amazon EventBridge": {
        "description": "Size of the payload, Number of AWS management events, Number of AWS opt-in data events, Number of custom events",
        "fields": {
            "size_of_the_payload": "Size of the payload",
            "number_of_aws_management_events": "Number of AWS management events",
            "number_of_aws_optin_data_events": "Number of AWS opt-in data events",
            "number_of_custom_events": "Number of custom events",
            "number_of_partner_events": "Number of partner events",
            "number_of_events_delivered_to_another_event_bus": "Number of events delivered to another event bus",
            "number_of_events_delivered_to_a_service_in_the_sam": "Number of events delivered to a service in the same account",
            "number_of_events_delivered_to_a_service_in_a_diffe": "Number of events delivered to a service in a different account",
            "number_of_invocations": "Number of invocations",
            "number_of_events": "Number of events",
            "number_of_replayed_events": "Number of replayed events",
            "number_of_requests": "Number of requests",
        },
    },
    "Amazon FSx for Lustre": {
        "description": "Storage capacity, Metadata IOPS (optional), Backup storage",
        "fields": {
            "storage_capacity": "Storage capacity",
            "metadata_iops_optional": "Metadata IOPS (optional)",
            "backup_storage": "Backup storage",
        },
    },
    "Amazon FSx for NetApp ONTAP": {
        "description": "Desired storage capacity, Desired additional SSD IOPS, Desired aggregate throughput, Read requests to capacity pool storage",
        "fields": {
            "desired_storage_capacity": "Desired storage capacity",
            "desired_additional_ssd_iops": "Desired additional SSD IOPS",
            "desired_aggregate_throughput": "Desired aggregate throughput",
            "read_requests_to_capacity_pool_storage": "Read requests to capacity pool storage",
            "write_requests_to_capacity_pool_storage": "Write requests to capacity pool storage",
            "backup_storage": "Backup storage",
        },
    },
    "Amazon FSx for OpenZFS": {
        "description": "Desired storage capacity",
        "fields": {
            "desired_storage_capacity": "Desired storage capacity",
        },
    },
    "Amazon FSx for Windows File Server": {
        "description": "Desired storage capacity, Desired aggregate throughput, Backup storage",
        "fields": {
            "desired_storage_capacity": "Desired storage capacity",
            "desired_aggregate_throughput": "Desired aggregate throughput",
            "backup_storage": "Backup storage",
        },
    },
    "Amazon File Cache": {
        "description": "Storage capacity",
        "fields": {
            "storage_capacity": "Storage capacity",
        },
    },
    "Amazon FinSpace Dataset Browser": {
        "description": "Number of users, Size of data to be stored, Total time spent: Small cluster (across all users), Total time spent: Medium cluster (across all users)",
        "fields": {
            "number_of_users": "Number of users",
            "size_of_data_to_be_stored": "Size of data to be stored",
            "total_time_spent_small_cluster_across_all_users": "Total time spent: Small cluster (across all users)",
            "total_time_spent_medium_cluster_across_all_users": "Total time spent: Medium cluster (across all users)",
            "total_time_spent_large_cluster_across_all_users": "Total time spent: Large cluster (across all users)",
            "total_time_spent_xlarge_cluster_across_all_users": "Total time spent: X-Large cluster (across all users)",
            "total_time_spent_xxlarge_cluster_across_all_users": "Total time spent: XX-Large cluster (across all users)",
        },
    },
    "Amazon Forecast": {
        "description": "Data imported, Training hours, Unique number of items, Number of forecast horizon data points",
        "fields": {
            "data_imported": "Data imported",
            "training_hours": "Training hours",
            "unique_number_of_items": "Unique number of items",
            "number_of_forecast_horizon_data_points": "Number of forecast horizon data points",
            "number_of_quantiles": "Number of quantiles",
            "forecasting_frequency": "Forecasting frequency",
        },
    },
    "Amazon Fraud Detector": {
        "description": "Event data processed and stored, Number of model versions, Training time per model version in hours, Number of active model versions",
        "fields": {
            "event_data_processed_and_stored": "Event data processed and stored",
            "number_of_model_versions": "Number of model versions",
            "training_time_per_model_version_in_hours": "Training time per model version in hours",
            "number_of_active_model_versions": "Number of active model versions",
            "number_of_monthly_predictions_with_online_fraud_in": "Number of monthly predictions with Online Fraud Insights (OFI) model type",
            "number_of_monthly_predictions_with_transaction_fra": "Number of monthly predictions with Transaction Fraud Insights (TFI) model type",
            "number_of_monthly_predictions_with_rules_only_no_m": "Number of monthly predictions with rules only (no ML model)",
        },
    },
    "Amazon GameLift Servers": {
        "description": "Peak concurrent players (peak CCU), Game sessions per instance, Players per game session",
        "fields": {
            "peak_concurrent_players_peak_ccu": "Peak concurrent players (peak CCU)",
            "game_sessions_per_instance": "Game sessions per instance",
            "players_per_game_session": "Players per game session",
            "operating_system": "_autosuggest:Select an instance",
        },
    },
    "Amazon GameLift Streams": {
        "description": "Estimated Daily Active Users, Estimated stream hours per user",
        "fields": {
            "estimated_daily_active_users": "Estimated Daily Active Users",
            "estimated_stream_hours_per_user": "Estimated stream hours per user",
        },
    },
    "Amazon GuardDuty": {
        "description": "AWS CloudTrail Management Event Analysis, EC2 VPC Flow Log Analysis, EC2 DNS Query Log Analysis, AWS CloudTrail S3 Data Event Analysis",
        "fields": {
            "aws_cloudtrail_management_event_analysis": "AWS CloudTrail Management Event Analysis",
            "ec2_vpc_flow_log_analysis": "EC2 VPC Flow Log Analysis",
            "ec2_dns_query_log_analysis": "EC2 DNS Query Log Analysis",
            "aws_cloudtrail_s3_data_event_analysis": "AWS CloudTrail S3 Data Event Analysis",
            "amazon_eks_audit_logs_analysis": "Amazon EKS Audit Logs Analysis",
            "ebs_volume_data_scan_analysis": "EBS Volume Data Scan Analysis",
            "total_size_of_s3_objects_scanned_per_month": "Total Size of S3 Objects scanned per month",
            "number_of_put_requests_monitored_per_month": "Number of PUT requests monitored per month",
            "enter_the_amount_of_data_scanned_from_ebs_snapshot": "Enter the amount of data scanned from EBS snapshots per month",
            "enter_the_amount_of_data_scanned_from_ec2_ami_per_": "Enter the amount of data scanned from EC2 AMI per month",
            "enter_the_amount_of_data_scanned_from_s3_recovery_": "Enter the amount of data scanned from S3 Recovery Point per month",
            "rds_provisioned_instance_vcpu": "RDS provisioned instance vCPU",
            "aurora_serverless_v2_instances_acus": "Aurora Serverless v2 instances ACUs",
            "lambda_vpc_flow_log_analysis": "Lambda VPC Flow Log Analysis",
            "amazon_eks_runtime_monitoring_analysis": "Amazon EKS Runtime Monitoring Analysis",
            "amazon_ecs_runtime_monitoring_analysis": "Amazon ECS Runtime Monitoring Analysis",
            "amazon_ec2_runtime_monitoring_analysis": "Amazon EC2 Runtime Monitoring Analysis",
        },
    },
    "Amazon Healthlake": {
        "description": "Additional Data Storage, Total Number Of Queries per Month, Number Of NLP Characters, Exported Data per GB",
        "fields": {
            "additional_data_storage": "Additional Data Storage",
            "total_number_of_queries_per_month": "Total Number Of Queries per Month",
            "number_of_nlp_characters": "Number Of NLP Characters",
            "exported_data_per_gb": "Exported Data per GB",
            "number_of_notifications_to_amazon_eventbridge": "Number of notifications to Amazon EventBridge",
            "number_of_notifications_to_resthook": "Number of notifications to REST-Hook",
        },
    },
    "Amazon Inspector": {
        "description": "Average* No. of EC2 instances scanned per month, Total number of newly pushed container images per month, Total number of automated rescans per image per month, Average number of Lambda functions scanned in a month",
        "fields": {
            "average_no_of_ec2_instances_scanned_per_month": "Average* No. of EC2 instances scanned per month",
            "total_number_of_newly_pushed_container_images_per_": "Total number of newly pushed container images per month",
            "total_number_of_automated_rescans_per_image_per_mo": "Total number of automated rescans per image per month",
            "average_number_of_lambda_functions_scanned_in_a_mo": "Average number of Lambda functions scanned in a month",
            "total_number_of_repositories": "Total number of repositories",
            "number_of_sast_periodic_scans_per_repository_per_m": "Number of SAST periodic scans per repository per month",
            "number_of_sca_periodc_scans_per_repository_per_mon": "Number of SCA periodc scans per repository per month",
            "number_of_iac_periodic_scans_per_repository_per_mo": "Number of IaC periodic scans per repository per month",
            "total_number_of_ondemand_scans_across_each_scantyp": "Total Number of on-demand scans (across each scan-type including SAST, SCA and IaC) per repository per month",
            "total_number_of_changebased_scans_across_each_scan": "Total number of change-based scans (across each scan-type including SAST, SCA, IaC) per repository per month (including pull request/merge request or push) Enter a number",
        },
    },
    "Amazon Kendra": {
        "description": "Amazon Kendra - no additional configuration",
        "fields": {
        },
    },
    "Amazon Keyspaces": {
        "description": "Storage, Number of writes, Number of reads, Number of TTL delete operations",
        "fields": {
            "storage": "Storage",
            "number_of_writes": "Number of writes",
            "number_of_reads": "Number of reads",
            "number_of_ttl_delete_operations": "Number of TTL delete operations",
        },
    },
    "Amazon Kinesis Data Streams": {
        "description": "Number of records, Average record size, Number of Consumer Applications, Number of days for data retention",
        "fields": {
            "number_of_records": "Number of records",
            "average_record_size": "Average record size",
            "number_of_consumer_applications": "Number of Consumer Applications",
            "number_of_days_for_data_retention": "Number of days for data retention",
            "number_of_enhanced_fanout_consumers": "Number of Enhanced fan-out consumers",
        },
    },
    "Amazon Kinesis Video Streams": {
        "description": "Number of devices, Average bitrate, Duration of video streamed to Amazon Kinesis Video Streams (per device), Duration of video playback over HLS or MPEG-DASH (per camera)",
        "fields": {
            "number_of_devices": "Number of devices",
            "average_bitrate": "Average bitrate",
            "duration_of_video_streamed_to_amazon_kinesis_video": "Duration of video streamed to Amazon Kinesis Video Streams (per device)",
            "duration_of_video_playback_over_hls_or_mpegdash_pe": "Duration of video playback over HLS or MPEG-DASH (per camera)",
            "duration_of_video_consumed_by_other_applications_p": "Duration of video consumed by other applications (per camera)",
            "average_length_of_each_webrtc_session_for_live_vie": "Average length of each WebRTC session (for live view)",
            "turn_usage_enter_the_percentage": "TURN Usage Enter the percentage",
            "average_retention_for_video": "Average retention for video",
            "images_extracted_per_camera_1080p_resolution_strea": "Images extracted per camera (1080p resolution stream or lower)",
            "images_extracted_per_camera_greater_than_1080p_res": "Images extracted per camera (greater than 1080p resolution stream)",
        },
    },
    "Amazon Lightsail": {
        "description": "Number of servers, Server utilization, Number of containers, Container utilization",
        "fields": {
            "number_of_servers": "Number of servers",
            "instance_type": "_autosuggest:Select an instance",
            "server_utilization": "Server utilization",
            "number_of_containers": "Number of containers",
            "container_utilization": "Container utilization",
        },
    },
    "Amazon Location Service": {
        "description": "Dynamic Maps, Static Maps, Open Data Dynamic Maps",
        "fields": {
            "dynamic_maps": "Dynamic Maps",
            "static_maps": "Static Maps",
            "open_data_dynamic_maps": "Open Data Dynamic Maps",
        },
    },
    "Amazon Lookout for Metrics": {
        "description": "Total number of measures, Total number of dimension values",
        "fields": {
            "total_number_of_measures": "Total number of measures",
            "total_number_of_dimension_values": "Total number of dimension values",
        },
    },
    "Amazon Lookout for Vision": {
        "description": "Number of plants, Number of production lines per plant, Number of inspection points per production line, Number of cameras per inspection point",
        "fields": {
            "number_of_plants": "Number of plants",
            "number_of_production_lines_per_plant": "Number of production lines per plant",
            "number_of_inspection_points_per_production_line": "Number of inspection points per production line",
            "number_of_cameras_per_inspection_point": "Number of cameras per inspection point",
            "time_to_train_initial_model_hours": "Time to train initial model (hours)",
            "average_number_of_model_retrains_per_model_per_mon": "Average number of model retrains per model per month",
            "number_of_inference_units": "Number of inference units",
            "number_of_production_shifts_per_day": "Number of production shifts per day",
            "production_hours_per_shift": "Production hours per shift",
            "production_days_per_month": "Production days per month",
        },
    },
    "Amazon MQ": {
        "description": "Number of Brokers running, Storage per Broker, Enter Amount",
        "fields": {
            "number_of_brokers_running": "Number of Brokers running",
            "storage_per_broker": "Storage per Broker",
            "enter_amount": "Enter Amount",
        },
    },
    "Amazon Macie": {
        "description": "Number of S3 buckets, Total bytes in S3 storage, Number of objects monitored for automated data discovery",
        "fields": {
            "number_of_s3_buckets": "Number of S3 buckets",
            "total_bytes_in_s3_storage": "Total bytes in S3 storage",
            "number_of_objects_monitored_for_automated_data_dis": "Number of objects monitored for automated data discovery",
        },
    },
    "Amazon Managed Grafana": {
        "description": "Number of active editors/administrators, Number of active viewers",
        "fields": {
            "number_of_active_editorsadministrators": "Number of active editors/administrators",
            "number_of_active_viewers": "Number of active viewers",
        },
    },
    "Amazon Managed Service for Apache Flink": {
        "description": "Apache Flink applications, Apache Flink KPUs, Durable application backups maintained, Durable application backup storage (average size)",
        "fields": {
            "apache_flink_applications": "Apache Flink applications",
            "apache_flink_kpus": "Apache Flink KPUs",
            "durable_application_backups_maintained": "Durable application backups maintained",
            "durable_application_backup_storage_average_size": "Durable application backup storage (average size)",
            "studio_applications": "Studio applications",
        },
    },
    "Amazon Managed Service for Prometheus": {
        "description": "Average active time series, Avg Collection Interval (in seconds), Retention Period (in days), Average Number of Dashboard users per day",
        "fields": {
            "average_active_time_series": "Average active time series",
            "avg_collection_interval_in_seconds": "Avg Collection Interval (in seconds)",
            "retention_period_in_days": "Retention Period (in days)",
            "average_number_of_dashboard_users_per_day": "Average Number of Dashboard users per day",
            "number_of_prometheus_rules": "Number of Prometheus rules",
            "average_rule_execution_interval_in_seconds": "Average rule execution interval (in seconds)",
            "average_number_of_queries_per_day_per_dashboard_us": "Average number of queries per day per dashboard user",
            "average_samples_per_query_for_monitoring_queries": "Average samples per query for Monitoring queries",
            "average_samples_per_query_for_alerting_queries": "Average samples per query for Alerting queries",
            "number_of_collectors": "Number of collectors",
            "number_of_samples_collected": "Number of Samples collected",
        },
    },
    "Amazon Managed Streaming for Apache Kafka (MSK)": {
        "description": "Number of Kafka broker nodes, Storage per Broker, Desired Provisioned Storage Throughput (MiBps), Number of authentication schemes configured for private connectivity",
        "fields": {
            "number_of_kafka_broker_nodes": "Number of Kafka broker nodes",
            "instance_type": "_autosuggest:Select an instance",
            "storage_per_broker": "Storage per Broker",
            "desired_provisioned_storage_throughput_mibps": "Desired Provisioned Storage Throughput (MiBps)",
            "number_of_authentication_schemes_configured_for_pr": "Number of authentication schemes configured for private connectivity",
            "data_processed_for_private_connectivity": "Data processed for private connectivity",
            "enter_amount": "Enter Amount",
        },
    },
    "Amazon Managed Workflows for Apache Airflow": {
        "description": "Minimum workers, Maximum workers, Hours at maximum workers, Minimum web servers",
        "fields": {
            "minimum_workers": "Minimum workers",
            "maximum_workers": "Maximum workers",
            "hours_at_maximum_workers": "Hours at maximum workers",
            "minimum_web_servers": "Minimum web servers",
            "maximum_web_servers": "Maximum web servers",
            "hours_at_maximum_web_servers": "Hours at maximum web servers",
            "number_of_schedulers": "Number of schedulers",
            "data_storage_size": "Data storage size",
        },
    },
    "Amazon MemoryDB": {
        "description": "Number of nodes, Utilization (On-Demand only), Nodes, Data Written",
        "fields": {
            "number_of_nodes": "_autosuggest:Select an instance",
            "number_of_nodes_2": "Number of nodes",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "data_written": "Data Written",
            "snapshot_storage": "Snapshot storage",
        },
    },
    "Amazon Neptune": {
        "description": "Number of instances, Usage (Neptune instances), Number of workbench instances, Usage (Neptune Workbench instances)",
        "fields": {
            "number_of_instances": "Number of instances",
            "instance_type": "_autosuggest:Select an instance",
            "usage_neptune_instances": "Usage (Neptune instances)",
            "number_of_workbench_instances": "Number of workbench instances",
            "usage_neptune_workbench_instances": "Usage (Neptune Workbench instances)",
            "data_stored": "Data stored",
            "number_of_io_operations_requests": "Number of I/O operations (Requests)",
        },
    },
    "Amazon OpenSearch Service": {
        "description": "Nodes, Utilization (On-Demand only), Number of instances, Storage amount per volume (gp3)",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "number_of_instances": "Number of instances",
            "storage_amount_per_volume_gp3": "Storage amount per volume (gp3)",
            "provisioning_iops_per_volume_gp3": "Provisioning IOPS per volume (gp3)",
            "number_of_nodes": "Number of nodes",
            "utilization_ondemand_only_2": "Utilization (On-Demand only)",
        },
    },
    "Amazon Personalize": {
        "description": "Amazon Personalize - no additional configuration",
        "fields": {
        },
    },
    "Amazon Pinpoint": {
        "description": "Number of push notifications, Number of in-app message requests",
        "fields": {
            "number_of_push_notifications": "Number of push notifications",
            "number_of_inapp_message_requests": "Number of in-app message requests",
        },
    },
    "Amazon Polly": {
        "description": "Number of requests (Standard Text-to-Speech), Number of characters per request including white spaces, but excluding SSML",
        "fields": {
            "number_of_requests_standard_texttospeech": "Number of requests (Standard Text-to-Speech)",
            "number_of_characters_per_request_including_white_s": "Number of characters per request including white spaces, but excluding SSML",
        },
    },
    "Amazon Quantum Ledger Database (QLDB)": {
        "description": "Number of Write I/Os, Number of Read I/Os, Journal Storage",
        "fields": {
            "number_of_write_ios": "Number of Write I/Os",
            "number_of_read_ios": "Number of Read I/Os",
            "journal_storage": "Journal Storage",
        },
    },
    "Amazon QuickSight": {
        "description": "Number of Readers, Number of Authors",
        "fields": {
            "number_of_readers": "Number of Readers",
            "number_of_authors": "Number of Authors",
        },
    },
    "Amazon RDS Custom for Oracle": {
        "description": "Number of RDS Custom for Oracle instances, Utilization (On-Demand only), Storage amount",
        "fields": {
            "number_of_rds_custom_for_oracle_instances": "Number of RDS Custom for Oracle instances",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS Custom for SQL Server": {
        "description": "Number of RDS Custom for SQL Server instances, Utilization (On-Demand only), Storage amount",
        "fields": {
            "number_of_rds_custom_for_sql_server_instances": "Number of RDS Custom for SQL Server instances",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS for Db2": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS for MariaDB": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS for MySQL": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount, Number of hours running on Amazon RDS Extended Support",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
            "number_of_hours_running_on_amazon_rds_extended_sup": "Number of hours running on Amazon RDS Extended Support",
        },
    },
    "Amazon RDS for Oracle": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS for PostgreSQL": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount, Number of hours running on Amazon RDS Extended Support",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
            "number_of_hours_running_on_amazon_rds_extended_sup": "Number of hours running on Amazon RDS Extended Support",
        },
    },
    "Amazon RDS for SQL server": {
        "description": "Nodes, Utilization (On-Demand only), Storage amount",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon RDS on AWS Outposts": {
        "description": "Number of RDS for Outposts instances, Utilization (On-Demand only)",
        "fields": {
            "number_of_rds_for_outposts_instances": "Number of RDS for Outposts instances",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
        },
    },
    "Amazon Redshift": {
        "description": "Nodes, Utilization (On-Demand only)",
        "fields": {
            "nodes": "Nodes",
            "instance_type": "_autosuggest:Select an instance",
            "utilization_ondemand_only": "Utilization (On-Demand only)",
        },
    },
    "Amazon Rekognition": {
        "description": "Number of images processed with labels API calls per month, Number of images processed with content moderation API calls per month, Number of images processed with detect text API calls per month, Number of images processed with celebrity API calls per month",
        "fields": {
            "number_of_images_processed_with_labels_api_calls_p": "Number of images processed with labels API calls per month",
            "number_of_images_processed_with_content_moderation": "Number of images processed with content moderation API calls per month",
            "number_of_images_processed_with_detect_text_api_ca": "Number of images processed with detect text API calls per month",
            "number_of_images_processed_with_celebrity_api_call": "Number of images processed with celebrity API calls per month",
            "number_of_images_processed_with_ppe_detection_api_": "Number of images processed with PPE detection API calls per month",
            "number_of_images_processed_with_image_properties_a": "Number of images processed with Image Properties API calls per month",
            "number_of_detectfaces_api_calls_per_month": "Number of DetectFaces API calls per month",
        },
    },
    "Amazon Route 53": {
        "description": "Hosted Zones, Additional Records in Hosted Zones, Traffic Flow, Standard queries",
        "fields": {
            "hosted_zones": "Hosted Zones",
            "additional_records_in_hosted_zones": "Additional Records in Hosted Zones",
            "traffic_flow": "Traffic Flow",
            "standard_queries": "Standard queries",
            "latency_based_routing_queries": "Latency based routing queries",
            "geo_dns_queries": "Geo DNS queries",
            "ipbased_routing_queries": "IP-based routing queries",
            "ip_cidr_blocks": "IP (CIDR) blocks",
            "basic_checks_within_aws": "Basic Checks Within AWS",
            "basic_checks_outside_of_aws": "Basic Checks Outside of AWS",
            "https_checks_within_aws": "HTTPS Checks Within AWS",
            "https_checks_outside_of_aws": "HTTPS Checks Outside of AWS",
            "string_matching_checks_within_aws": "String Matching Checks Within AWS",
            "string_matching_checks_outside_of_aws": "String Matching Checks Outside of AWS",
            "fast_interval_checks_within_aws": "Fast Interval Checks Within AWS",
            "fast_interval_checks_outside_of_aws": "Fast Interval Checks Outside of AWS",
            "latency_measurement_checks_within_aws": "Latency Measurement Checks Within AWS",
            "latency_measurement_checks_outside_of_aws": "Latency Measurement Checks Outside of AWS",
            "number_of_elastic_network_interfaces": "Number of Elastic Network Interfaces",
            "recursive_average_dns_queries": "Recursive average DNS queries",
            "number_of_domains_stored": "Number of domains stored",
            "dns_queries": "DNS queries",
            "number_of_vpcs_associated_to_the_rule_group": "Number of VPCs associated to the rule group",
            "number_of_hours_the_rule_group_is_associated_for": "Number of hours the rule group is associated for",
        },
    },
    "Amazon SageMaker": {
        "description": "Number of data scientist(s), Number of Studio Notebook instances per data scientist, Studio Notebook hour(s) per day, Studio Notebook day(s) per month",
        "fields": {
            "number_of_data_scientists": "Number of data scientist(s)",
            "number_of_studio_notebook_instances_per_data_scien": "Number of Studio Notebook instances per data scientist",
            "studio_notebook_hours_per_day": "Studio Notebook hour(s) per day",
            "studio_notebook_days_per_month": "Studio Notebook day(s) per month",
            "number_of_ondemand_notebook_instances_per_data_sci": "Number of On-Demand Notebook instances per data scientist",
            "ondemand_notebook_hours_per_day": "On-Demand Notebook hour(s) per day",
            "ondemand_notebook_days_per_month": "On-Demand Notebook day(s) per month",
            "storage_amount": "Storage amount",
        },
    },
    "Amazon SageMaker Ground Truth": {
        "description": "Number of dataset objects, Number of workers per dataset object, Number of human tasks per month",
        "fields": {
            "number_of_dataset_objects": "Number of dataset objects",
            "number_of_workers_per_dataset_object": "Number of workers per dataset object",
            "number_of_human_tasks_per_month": "Number of human tasks per month",
        },
    },
    "Amazon Security Lake": {
        "description": "CloudTrail events",
        "fields": {
            "cloudtrail_events": "CloudTrail events",
        },
    },
    "Amazon Simple Email Service (SES)": {
        "description": "Number of Open Ingress Endpoint(s), Number of Emails processed by Mail Manager, Email messages sent from EC2, Attachment data sent from EC2",
        "fields": {
            "number_of_open_ingress_endpoints": "Number of Open Ingress Endpoint(s)",
            "number_of_emails_processed_by_mail_manager": "Number of Emails processed by Mail Manager",
            "email_messages_sent_from_ec2": "Email messages sent from EC2",
            "attachment_data_sent_from_ec2": "Attachment data sent from EC2",
            "email_messages_sent_from_email_client": "Email messages sent from email client",
            "attachment_data_sent_from_email_client": "Attachment data sent from email client",
            "email_messages_received": "Email messages received",
            "average_size_of_email_processed_by_mail_manager": "Average size of email processed by Mail Manager",
            "email_message_sent_via_dedicated_ips_managed": "Email message sent via dedicated IPs (managed)",
            "number_of_dedicated_ipstandard_addresses": "Number of dedicated IP(standard) addresses",
            "gigabytes_inserted_indexed": "Gigabytes Inserted & Indexed",
            "gigabytes_already_stored": "Gigabytes Already Stored",
        },
    },
    "Amazon Simple Notification Service (SNS)": {
        "description": "Requests, HTTP/HTTPS Notifications, EMAIL/EMAIL-JSON Notifications, SQS Notifications",
        "fields": {
            "requests": "Requests",
            "httphttps_notifications": "HTTP/HTTPS Notifications",
            "emailemailjson_notifications": "EMAIL/EMAIL-JSON Notifications",
            "sqs_notifications": "SQS Notifications",
            "amazon_web_services_lambda": "Amazon Web Services Lambda",
            "amazon_kinesis_data_firehose": "Amazon Kinesis Data Firehose",
            "mobile_push_notifications": "Mobile Push Notifications",
            "enter_amount": "Enter Amount",
            "publish_and_delivery_message_scanning": "Publish and Delivery Message Scanning",
            "the_amount_of_outbound_payload_data_scanned_per_mo": "The amount of outbound payload data scanned per month",
        },
    },
    "Amazon Simple Queue Service (SQS)": {
        "description": "Standard queue requests, FIFO queue requests, Fair queue requests, Enter Amount",
        "fields": {
            "standard_queue_requests": "Standard queue requests",
            "fifo_queue_requests": "FIFO queue requests",
            "fair_queue_requests": "Fair queue requests",
            "enter_amount": "Enter Amount",
        },
    },
    "Amazon Simple Storage Service (S3)": {
        "description": "S3 Standard storage, PUT, COPY, POST, LIST requests to S3 Standard, GET, SELECT, and all other requests from S3 Standard, Data returned by S3 Select",
        "fields": {
            "s3_standard_storage": "S3 Standard storage",
            "put_copy_post_list_requests_to_s3_standard": "PUT, COPY, POST, LIST requests to S3 Standard",
            "get_select_and_all_other_requests_from_s3_standard": "GET, SELECT, and all other requests from S3 Standard",
            "data_returned_by_s3_select": "Data returned by S3 Select",
            "enter_amount": "Enter Amount",
        },
    },
    "Amazon Simple Workflow Service (SWF)": {
        "description": "Workflow Executions, Total Tasks, Markers, Timers and Signals, Workflow lifetime, Workflow retention",
        "fields": {
            "workflow_executions": "Workflow Executions",
            "total_tasks_markers_timers_and_signals": "Total Tasks, Markers, Timers and Signals",
            "workflow_lifetime": "Workflow lifetime",
            "workflow_retention": "Workflow retention",
        },
    },
    "Amazon Textract": {
        "description": "Number of pages, Percent of pages with text (Detect Document Text API) Enter %",
        "fields": {
            "number_of_pages": "Number of pages",
            "percent_of_pages_with_text_detect_document_text_ap": "Percent of pages with text (Detect Document Text API) Enter %",
        },
    },
    "Amazon Timestream": {
        "description": "Estimated Monthly Storage",
        "fields": {
            "estimated_monthly_storage": "Estimated Monthly Storage",
        },
    },
    "Amazon Transcribe": {
        "description": "Amazon Transcribe - no additional configuration",
        "fields": {
        },
    },
    "Amazon Transcribe Medical": {
        "description": "Number of minutes of medical audio transcription per month",
        "fields": {
            "number_of_minutes_of_medical_audio_transcription_p": "Number of minutes of medical audio transcription per month",
        },
    },
    "Amazon Translate": {
        "description": "Number of characters including white spaces and punctuations (Standard Real-Time Translation)",
        "fields": {
            "number_of_characters_including_white_spaces_and_pu": "Number of characters including white spaces and punctuations (Standard Real-Time Translation)",
        },
    },
    "Amazon Verified Permissions": {
        "description": "Number of Single Authorization Requests, Number of Batch Authorization Requests, Number of Policy Management Requests",
        "fields": {
            "number_of_single_authorization_requests": "Number of Single Authorization Requests",
            "number_of_batch_authorization_requests": "Number of Batch Authorization Requests",
            "number_of_policy_management_requests": "Number of Policy Management Requests",
        },
    },
    "Amazon Virtual Private Cloud (VPC)": {
        "description": "NAT Gateway instances, Site-to-Site VPN, Client VPN connections, subnet associations",
        "fields": {
            "nat_gateway_radio": "_radio",
            "nat_gateways": "Number of Instances",
            "vpn_connections": "Number of Site-to-Site VPN Connections",
            "vpn_duration": "Average duration for each connection",
            "subnet_associations": "Number of subnet associations",
            "client_vpn_connections": "Number of active Client VPN connections (or users)",
            "working_days_per_month": "Working days per month",
        },
    },
    "Amazon WorkSpaces": {
        "description": "Number of WorkSpaces, Billing option",
        "fields": {
            "number_of_workspaces": "Number of WorkSpaces",
            "billing_option": "Billing option",
        },
    },
    "Amazon WorkSpaces Applications": {
        "description": "Number of users per month, Number of working hours per day, Instance Disk Volume size, Days in week",
        "fields": {
            "operating_system": "_autosuggest:Select an instance",
            "number_of_users_per_month": "Number of users per month",
            "number_of_working_hours_per_day": "Number of working hours per day",
            "instance_disk_volume_size": "Instance Disk Volume size",
            "days_in_week": "Days in week",
            "peak_duration_hours_per_day": "Peak duration (hours) per day",
            "average_offpeak_concurrent_users_per_hour": "Average off-peak concurrent users per hour",
            "average_peak_concurrent_users_per_hour": "Average peak concurrent users per hour",
            "days_in_weekend": "Days in weekend",
        },
    },
    "Elastic Load Balancing": {
        "description": "Number of Application Load Balancers, Processed bytes (Lambda functions as targets), Average number of new connections per ALB, Average number of requests per second per ALB",
        "fields": {
            "number_of_application_load_balancers": "Number of Application Load Balancers",
            "processed_bytes_lambda_functions_as_targets": "Processed bytes (Lambda functions as targets)",
            "average_number_of_new_connections_per_alb": "Average number of new connections per ALB",
            "average_number_of_requests_per_second_per_alb": "Average number of requests per second per ALB",
            "average_number_of_rule_evaluations_per_request": "Average number of rule evaluations per request",
        },
    },
    "Windows Server and SQL Server on Amazon EC2": {
        "description": "Machine description, Storage amount (GB), IOPS, Throughput (MiB/s)",
        "fields": {
            "machine_description": "Machine description",
            "storage_amount_gb": "Storage amount (GB)",
            "iops": "IOPS",
            "throughput_mibs": "Throughput (MiB/s)",
            "number_of_vcpus": "Number of vCPUs",
            "memory_gib": "Memory (GiB)",
            "quantity": "Quantity",
            "number_of_passive_instances": "Number of passive instances",
        },
    },
}