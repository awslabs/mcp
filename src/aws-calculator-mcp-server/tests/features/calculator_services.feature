Feature: AWS Pricing Calculator - Service Configuration Certification
  As a cloud architect using the AWS Calculator MCP
  I want to create estimates for all supported AWS services
  So that I can generate accurate shareable pricing links

  Background:
    Given the AWS Calculator browser is initialized
    And the calculator is at the add service page

  # ============================================================
  # COMPUTE SERVICES
  # ============================================================

  @compute @ec2
  Scenario Outline: Configure Amazon EC2 - <os> on <tenancy>
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<os>" from dropdown "Operating system"
    And I select "<tenancy>" from dropdown "Tenancy"
    And I fill "Number of instances" with "2"
    And I select "m6i.xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

    Examples: OS and tenancy combinations
      | os                          | tenancy             |
      | Linux                       | Shared Instances    |
      | Windows Server              | Shared Instances    |
      | Red Hat Enterprise Linux    | Shared Instances    |
      | SUSE Linux Enterprise Server | Shared Instances   |
      | Ubuntu Pro                  | Shared Instances    |
      | Linux                       | Dedicated Instances |
      | Windows Server              | Dedicated Instances |

  @compute @lightsail
  Scenario: Configure Amazon Lightsail with all fields
    Given I search for "Amazon Lightsail"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of servers" with "3"
    And I select "medium" via autosuggest for "Select an instance"
    And I fill "Server utilization" with "85"
    And I fill "Number of containers" with "2"
    And I fill "Container utilization" with "90"
    And I click Save and add service
    Then the service "Amazon Lightsail" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lambda
  Scenario Outline: Configure AWS Lambda - <architecture> architecture
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<architecture>" from dropdown "Architecture"
    And I fill "Number of requests" with "1000000"
    And I fill "Duration of each request (in ms)" with "250"
    And I fill "Amount of memory allocated" with "1024"
    And I fill "Amount of ephemeral storage allocated" with "512"
    And I fill "Concurrency" with "100"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Architecture variants
      | architecture |
      | x86          |
      | Arm          |

  @compute @lambda @provisioned
  Scenario: Configure AWS Lambda with Provisioned Concurrency
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "x86" from dropdown "Architecture"
    And I fill "Number of requests" with "5000000"
    And I fill "Duration of each request (in ms)" with "100"
    And I fill "Amount of memory allocated" with "512"
    And I fill "Amount of ephemeral storage allocated" with "512"
    And I fill "Concurrency" with "500"
    And I fill "Duration of each provisioned request (in ms)" with "80"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

  @compute @fargate
  Scenario Outline: Configure AWS Fargate - <os> on <arch>
    Given I search for "AWS Fargate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<os>" from dropdown "Operating system"
    And I select "<arch>" from dropdown "CPU Architecture"
    And I fill "Number of tasks or pods" with "10"
    And I fill "Average duration" with "120"
    And I fill "Amount of memory allocated" with "4"
    And I fill "Amount of ephemeral storage allocated for Amazon ECS" with "30"
    And I click Save and add service
    Then the service "AWS Fargate" should be added successfully
    And a shareable estimate URL should be generated

    Examples: OS and architecture combinations
      | os      | arch |
      | Linux   | x86  |
      | Linux   | ARM  |
      | Windows | x86  |

  @compute @fargate @high-memory
  Scenario: Configure AWS Fargate with high memory workload
    Given I search for "AWS Fargate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "x86" from dropdown "CPU Architecture"
    And I fill "Number of tasks or pods" with "50"
    And I fill "Average duration" with "3600"
    And I fill "Amount of memory allocated" with "16"
    And I fill "Amount of ephemeral storage allocated for Amazon ECS" with "100"
    And I click Save and add service
    Then the service "AWS Fargate" should be added successfully
    And a shareable estimate URL should be generated

  @compute @app-runner
  Scenario: Configure AWS App Runner - standard workload
    Given I search for "AWS App Runner"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Concurrency" with "80"
    And I fill "Minimum provisioned container instances" with "2"
    And I fill "Peak traffic hours" with "8"
    And I fill "Number of requests during peak traffic (requests/second)" with "500"
    And I fill "Number of requests during off-peak traffic (requests/second)" with "50"
    And I click Save and add service
    Then the service "AWS App Runner" should be added successfully
    And a shareable estimate URL should be generated

  @compute @app-runner @high-traffic
  Scenario: Configure AWS App Runner - high traffic workload
    Given I search for "AWS App Runner"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Concurrency" with "200"
    And I fill "Minimum provisioned container instances" with "10"
    And I fill "Peak traffic hours" with "12"
    And I fill "Number of requests during peak traffic (requests/second)" with "5000"
    And I fill "Number of requests during off-peak traffic (requests/second)" with "500"
    And I click Save and add service
    Then the service "AWS App Runner" should be added successfully
    And a shareable estimate URL should be generated

  @compute @elastic-vmware
  Scenario: Configure Amazon Elastic VMware Service with all fields
    Given I search for "Amazon Elastic VMware Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Instances" with "3"
    And I click Save and add service
    Then the service "Amazon Elastic VMware Service" should be added successfully
    And a shareable estimate URL should be generated

  @compute @eks
  Scenario: Configure Amazon EKS with all fields
    Given I search for "Amazon EKS"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of EKS Clusters" with "2"
    And I click Save and add service
    Then the service "Amazon EKS" should be added successfully
    And a shareable estimate URL should be generated

  @compute @emr
  Scenario: Configure Amazon EMR - small cluster
    Given I search for "Amazon EMR"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of master EMR nodes" with "1"
    And I fill "Utilization" with "100"
    And I fill "Number of core EMR nodes" with "4"
    And I click Save and add service
    Then the service "Amazon EMR" should be added successfully
    And a shareable estimate URL should be generated

  @compute @emr @large-cluster
  Scenario: Configure Amazon EMR - large cluster
    Given I search for "Amazon EMR"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of master EMR nodes" with "3"
    And I fill "Utilization" with "100"
    And I fill "Number of core EMR nodes" with "20"
    And I click Save and add service
    Then the service "Amazon EMR" should be added successfully
    And a shareable estimate URL should be generated

  @compute @amplify
  Scenario: Configure AWS Amplify with all fields
    Given I search for "AWS Amplify"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of build minutes" with "1000"
    And I fill "Data stored per month" with "50"
    And I fill "Data served per month" with "200"
    And I fill "Number of SSR requests" with "500000"
    And I fill "Duration of each request (in ms)" with "100"
    And I click Save and add service
    Then the service "AWS Amplify" should be added successfully
    And a shareable estimate URL should be generated

  @compute @step-functions
  Scenario: Configure AWS Step Functions with all fields
    Given I search for "AWS Step Functions"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Workflow requests" with "100000"
    And I fill "State transitions per workflow" with "8"
    And I click Save and add service
    Then the service "AWS Step Functions" should be added successfully
    And a shareable estimate URL should be generated

  @compute @mainframe-modernization
  Scenario: Configure AWS Mainframe Modernization with all fields
    Given I search for "AWS Mainframe Modernization"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of instances" with "2"
    And I fill "Monthly utilization" with "730"
    And I click Save and add service
    Then the service "AWS Mainframe Modernization" should be added successfully
    And a shareable estimate URL should be generated

  @compute @pcs
  Scenario: Configure AWS PCS with all fields
    Given I search for "AWS PCS"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of PCS Clusters" with "2"
    And I fill "Length of time cluster is running" with "500"
    And I click Save and add service
    Then the service "AWS PCS" should be added successfully
    And a shareable estimate URL should be generated

  @compute @simspace-weaver
  Scenario: Configure AWS SimSpace Weaver with all fields
    Given I search for "AWS SimSpace Weaver"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of instances" with "4"
    And I select "c5.xlarge" via autosuggest for "Select an instance"
    And I fill "Usage" with "200"
    And I click Save and add service
    Then the service "AWS SimSpace Weaver" should be added successfully
    And a shareable estimate URL should be generated

  @compute @deadline-cloud
  Scenario: Configure AWS Deadline Cloud with all fields
    Given I search for "AWS Deadline Cloud"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Instance" with "10"
    And I select "c5.2xlarge" via autosuggest for "Select an instance"
    And I fill "Monthly utilization" with "500"
    And I fill "Storage per worker" with "100"
    And I fill "Utilization (On-Demand only)" with "80"
    And I click Save and add service
    Then the service "AWS Deadline Cloud" should be added successfully
    And a shareable estimate URL should be generated

  @compute @elastic-graphics
  Scenario: Configure Amazon Elastic Graphics with all fields
    Given I search for "Amazon Elastic Graphics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of nodes" with "2"
    And I select "eg1.2xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon Elastic Graphics" should be added successfully
    And a shareable estimate URL should be generated

  @compute @gamelift-servers
  Scenario: Configure Amazon GameLift Servers with all fields
    Given I search for "Amazon GameLift Servers"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Peak concurrent players (peak CCU)" with "1000"
    And I fill "Game sessions per instance" with "4"
    And I fill "Players per game session" with "64"
    And I select "c5.xlarge" via autosuggest for "Select an instance"
    And I click Save and add service
    Then the service "Amazon GameLift Servers" should be added successfully
    And a shareable estimate URL should be generated

  @compute @gamelift-streams
  Scenario: Configure Amazon GameLift Streams with all fields
    Given I search for "Amazon GameLift Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Estimated Daily Active Users" with "500"
    And I fill "Estimated stream hours per user" with "2"
    And I click Save and add service
    Then the service "Amazon GameLift Streams" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # DATABASE SERVICES
  # ============================================================

  @database @rds-postgresql
  Scenario Outline: Configure Amazon RDS for PostgreSQL - <deployment> with <storage_type>
    Given I search for "Amazon RDS for PostgreSQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I select "<storage_type>" from dropdown "Storage type"
    And I fill "Nodes" with "2"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon RDS for PostgreSQL" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment and storage combinations
      | deployment | storage_type                    |
      | Multi-AZ   | General Purpose SSD (gp2)       |
      | Multi-AZ   | General Purpose SSD (gp3)       |
      | Multi-AZ   | Provisioned IOPS SSD (io1)      |
      | Multi-AZ   | Provisioned IOPS SSD (io2)      |
      | Single-AZ  | General Purpose SSD (gp2)       |
      | Single-AZ  | General Purpose SSD (gp3)       |
      | Single-AZ  | Provisioned IOPS SSD (io1)      |
      | Single-AZ  | Provisioned IOPS SSD (io2)      |

  @database @rds-mysql
  Scenario Outline: Configure Amazon RDS for MySQL - <deployment> with <storage_type>
    Given I search for "Amazon RDS for MySQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I select "<storage_type>" from dropdown "Storage type"
    And I fill "Nodes" with "2"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon RDS for MySQL" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment and storage combinations
      | deployment | storage_type                    |
      | Multi-AZ   | General Purpose SSD (gp2)       |
      | Multi-AZ   | General Purpose SSD (gp3)       |
      | Multi-AZ   | Provisioned IOPS SSD (io1)      |
      | Multi-AZ   | Provisioned IOPS SSD (io2)      |
      | Single-AZ  | General Purpose SSD (gp2)       |
      | Single-AZ  | General Purpose SSD (gp3)       |
      | Single-AZ  | Provisioned IOPS SSD (io1)      |
      | Single-AZ  | Provisioned IOPS SSD (io2)      |

  @database @rds-mariadb
  Scenario Outline: Configure Amazon RDS for MariaDB - <deployment> with <storage_type>
    Given I search for "Amazon RDS for MariaDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I select "<storage_type>" from dropdown "Storage type"
    And I fill "Nodes" with "2"
    And I select "db.m6i.large" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon RDS for MariaDB" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment and storage combinations
      | deployment | storage_type               |
      | Multi-AZ   | General Purpose SSD (gp3)  |
      | Single-AZ  | General Purpose SSD (gp2)  |
      | Single-AZ  | Provisioned IOPS SSD (io1) |

  @database @rds-oracle
  Scenario Outline: Configure Amazon RDS for Oracle - <deployment> deployment
    Given I search for "Amazon RDS for Oracle"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I fill "Nodes" with "1"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon RDS for Oracle" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment variants
      | deployment |
      | Multi-AZ   |
      | Single-AZ  |

  @database @rds-sql-server
  Scenario Outline: Configure Amazon RDS for SQL server - <deployment> deployment
    Given I search for "Amazon RDS for SQL server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I fill "Nodes" with "1"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon RDS for SQL server" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment variants
      | deployment |
      | Multi-AZ   |
      | Single-AZ  |

  @database @rds-db2
  Scenario Outline: Configure Amazon RDS for Db2 - <deployment> deployment
    Given I search for "Amazon RDS for Db2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment Option"
    And I fill "Nodes" with "1"
    And I select "db.m6i.large" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon RDS for Db2" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment variants
      | deployment |
      | Multi-AZ   |
      | Single-AZ  |

  @database @rds-custom-oracle
  Scenario: Configure Amazon RDS Custom for Oracle with all fields
    Given I search for "Amazon RDS Custom for Oracle"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of RDS Custom for Oracle instances" with "1"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon RDS Custom for Oracle" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-custom-sql
  Scenario: Configure Amazon RDS Custom for SQL Server with all fields
    Given I search for "Amazon RDS Custom for SQL Server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of RDS Custom for SQL Server instances" with "1"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon RDS Custom for SQL Server" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-outposts
  Scenario: Configure Amazon RDS on AWS Outposts with all fields
    Given I search for "Amazon RDS on AWS Outposts"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of RDS for Outposts instances" with "2"
    And I select "db.m5.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon RDS on AWS Outposts" should be added successfully
    And a shareable estimate URL should be generated

  @database @aurora-mysql
  Scenario Outline: Configure Amazon Aurora MySQL-Compatible - <storage_mode> with <pricing>
    Given I search for "Amazon Aurora MySQL-Compatible"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<storage_mode>" from dropdown "Storage mode"
    And I select "<pricing>" from dropdown "Pricing model"
    And I fill "Nodes" with "2"
    And I select "db.r6g.large" via autosuggest for "Select an instance"
    And I fill "Utilization" with "100"
    And I fill "Storage amount" with "100"
    And I fill "Baseline IO rate" with "1000"
    And I click Save and add service
    Then the service "Amazon Aurora MySQL-Compatible" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Storage mode and pricing combinations
      | storage_mode         | pricing  |
      | Aurora Standard      | OnDemand |
      | Aurora Standard      | Reserved |
      | Aurora I/O-Optimized | OnDemand |
      | Aurora I/O-Optimized | Reserved |

  @database @aurora-postgresql
  Scenario Outline: Configure Amazon Aurora PostgreSQL-Compatible DB - <storage_mode> with <pricing>
    Given I search for "Amazon Aurora PostgreSQL-Compatible DB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<storage_mode>" from dropdown "Storage mode"
    And I select "<pricing>" from dropdown "Pricing model"
    And I fill "Quantity" with "2"
    And I select "db.r6g.large" via autosuggest for "Select an instance"
    And I fill "Utilization" with "100"
    And I fill "Storage amount" with "100"
    And I fill "Baseline IO rate" with "1000"
    And I click Save and add service
    Then the service "Amazon Aurora PostgreSQL-Compatible DB" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Storage mode and pricing combinations
      | storage_mode         | pricing  |
      | Aurora Standard      | OnDemand |
      | Aurora Standard      | Reserved |
      | Aurora I/O-Optimized | OnDemand |
      | Aurora I/O-Optimized | Reserved |

  @database @dynamodb
  Scenario Outline: Configure Amazon DynamoDB - <table_class> table class
    Given I search for "Amazon DynamoDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<table_class>" from dropdown "Table class"
    And I fill "Average item size (all attributes)" with "200"
    And I fill "Baseline write rate" with "100"
    And I fill "Peak write rate" with "500"
    And I fill "Duration of peak write activity" with "4"
    And I fill "Baseline read rate" with "500"
    And I fill "Peak read rate" with "2000"
    And I click Save and add service
    Then the service "Amazon DynamoDB" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Table class variants
      | table_class                |
      | Standard                   |
      | Standard-Infrequent Access |

  @database @dynamodb @high-throughput
  Scenario: Configure Amazon DynamoDB with high throughput workload
    Given I search for "Amazon DynamoDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Standard" from dropdown "Table class"
    And I fill "Average item size (all attributes)" with "1"
    And I fill "Baseline write rate" with "5000"
    And I fill "Peak write rate" with "25000"
    And I fill "Duration of peak write activity" with "2"
    And I fill "Baseline read rate" with "20000"
    And I fill "Peak read rate" with "100000"
    And I click Save and add service
    Then the service "Amazon DynamoDB" should be added successfully
    And a shareable estimate URL should be generated

  @database @documentdb
  Scenario Outline: Configure Amazon DocumentDB - <engine> engine
    Given I search for "Amazon DocumentDB (with MongoDB compatibility)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<engine>" from dropdown "Engine"
    And I fill "Quantity" with "3"
    And I select "db.r6g.large" via autosuggest for "Select an instance"
    And I fill "Server utilization" with "730"
    And I click Save and add service
    Then the service "Amazon DocumentDB (with MongoDB compatibility)" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Engine variants
      | engine                          |
      | Amazon DocumentDB Standard      |
      | Amazon DocumentDB I/O-Optimized |

  @database @neptune
  Scenario Outline: Configure Amazon Neptune - <storage_mode> storage
    Given I search for "Amazon Neptune"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<storage_mode>" from dropdown "Storage mode"
    And I fill "Number of instances" with "2"
    And I select "db.r6g.large" via autosuggest for "Select an instance"
    And I fill "Usage (Neptune instances)" with "100"
    And I fill "Data stored" with "50"
    And I click Save and add service
    Then the service "Amazon Neptune" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Storage mode variants
      | storage_mode          |
      | Neptune Standard      |
      | Neptune I/O-Optimized |

  @database @elasticache
  Scenario Outline: Configure Amazon ElastiCache - <engine> engine with <pricing>
    Given I search for "Amazon ElastiCache"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<engine>" from dropdown "Engine"
    And I select "<pricing>" from dropdown "Pricing model"
    And I fill "Nodes" with "3"
    And I select "cache.m5.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon ElastiCache" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Engine and pricing variants
      | engine    | pricing  |
      | Memcached | OnDemand |
      | Redis     | OnDemand |
      | Redis     | Reserved |
      | Valkey    | OnDemand |
      | Valkey    | Reserved |

  @database @memorydb
  Scenario: Configure Amazon MemoryDB - small cluster
    Given I search for "Amazon MemoryDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of nodes" with "3"
    And I select "db.r6g.large" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Data Written" with "50"
    And I fill "Snapshot storage" with "100"
    And I click Save and add service
    Then the service "Amazon MemoryDB" should be added successfully
    And a shareable estimate URL should be generated

  @database @memorydb @large-cluster
  Scenario: Configure Amazon MemoryDB - large cluster
    Given I search for "Amazon MemoryDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of nodes" with "9"
    And I select "db.r6g.2xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Data Written" with "500"
    And I fill "Snapshot storage" with "1000"
    And I click Save and add service
    Then the service "Amazon MemoryDB" should be added successfully
    And a shareable estimate URL should be generated

  @database @redshift
  Scenario: Configure Amazon Redshift - dc2 cluster
    Given I search for "Amazon Redshift"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Nodes" with "3"
    And I select "dc2.large" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon Redshift" should be added successfully
    And a shareable estimate URL should be generated

  @database @redshift @ra3
  Scenario: Configure Amazon Redshift - ra3 cluster
    Given I search for "Amazon Redshift"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Nodes" with "4"
    And I select "ra3.xlplus" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon Redshift" should be added successfully
    And a shareable estimate URL should be generated

  @database @keyspaces
  Scenario: Configure Amazon Keyspaces with all fields
    Given I search for "Amazon Keyspaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Storage" with "100"
    And I fill "Number of writes" with "10000"
    And I fill "Number of reads" with "50000"
    And I fill "Number of TTL delete operations" with "1000"
    And I click Save and add service
    Then the service "Amazon Keyspaces" should be added successfully
    And a shareable estimate URL should be generated

  @database @timestream
  Scenario: Configure Amazon Timestream with all fields
    Given I search for "Amazon Timestream"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Estimated Monthly Storage" with "500"
    And I click Save and add service
    Then the service "Amazon Timestream" should be added successfully
    And a shareable estimate URL should be generated

  @database @qldb
  Scenario: Configure Amazon Quantum Ledger Database (QLDB) with all fields
    Given I search for "Amazon Quantum Ledger Database (QLDB)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Write I/Os" with "100000"
    And I fill "Number of Read I/Os" with "500000"
    And I fill "Journal Storage" with "50"
    And I click Save and add service
    Then the service "Amazon Quantum Ledger Database (QLDB)" should be added successfully
    And a shareable estimate URL should be generated

  @database @opensearch
  Scenario Outline: Configure Amazon OpenSearch Service - <pricing> pricing
    Given I search for "Amazon OpenSearch Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<pricing>" from dropdown "Pricing model"
    And I fill "Nodes" with "3"
    And I select "m6g.large.search" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount per volume (gp3)" with "100"
    And I click Save and add service
    Then the service "Amazon OpenSearch Service" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Pricing variants
      | pricing  |
      | OnDemand |
      | Reserved |

  @database @opensearch @serverless
  Scenario: Configure Amazon OpenSearch Service with serverless configuration
    Given I search for "Amazon OpenSearch Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Nodes" with "6"
    And I select "r6g.large.search" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount per volume (gp3)" with "500"
    And I fill "Provisioning IOPS per volume (gp3)" with "3000"
    And I click Save and add service
    Then the service "Amazon OpenSearch Service" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # STORAGE SERVICES
  # ============================================================

  @storage @s3
  Scenario: Configure Amazon Simple Storage Service (S3) - standard workload
    Given I search for "Amazon Simple Storage Service (S3)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "S3 Standard storage" with "1000"
    And I fill "PUT, COPY, POST, LIST requests to S3 Standard" with "100000"
    And I fill "GET, SELECT, and all other requests from S3 Standard" with "500000"
    And I fill "Data returned by S3 Select" with "50"
    And I click Save and add service
    Then the service "Amazon Simple Storage Service (S3)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @s3 @high-volume
  Scenario: Configure Amazon Simple Storage Service (S3) - high volume
    Given I search for "Amazon Simple Storage Service (S3)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "S3 Standard storage" with "50000"
    And I fill "PUT, COPY, POST, LIST requests to S3 Standard" with "10000000"
    And I fill "GET, SELECT, and all other requests from S3 Standard" with "50000000"
    And I fill "Data returned by S3 Select" with "500"
    And I fill "Enter Amount" with "10000"
    And I click Save and add service
    Then the service "Amazon Simple Storage Service (S3)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ebs
  Scenario Outline: Configure Amazon Elastic Block Store (EBS) - <volume_type>
    Given I search for "Amazon Elastic Block Store (EBS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<volume_type>" from dropdown "Volume type"
    And I fill "Number of volumes" with "4"
    And I fill "Average duration of volume" with "730"
    And I fill "Storage amount per volume" with "500"
    And I fill "Amount changed per snapshot" with "10"
    And I click Save and add service
    Then the service "Amazon Elastic Block Store (EBS)" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Volume type variants
      | volume_type                         |
      | General Purpose SSD (gp2)           |
      | General Purpose SSD (gp3)           |
      | Provisioned IOPS SSD (io1)          |
      | Provisioned IOPS SSD (io2)          |
      | Throughput Optimized HDD (st 1)     |
      | Cold HDD (sc1)                      |
      | Magnetic (previous generation)      |

  @storage @efs
  Scenario Outline: Configure Amazon Elastic File System (EFS) - <throughput_mode> throughput
    Given I search for "Amazon Elastic File System (EFS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<throughput_mode>" from dropdown "Throughput mode"
    And I fill "Desired Storage Capacity" with "500"
    And I fill "Infrequent Access Tiering" with "20"
    And I fill "Infrequent Access Read" with "10"
    And I click Save and add service
    Then the service "Amazon Elastic File System (EFS)" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Throughput mode variants
      | throughput_mode        |
      | Elastic Throughput     |
      | Provisioned Throughput |

  @storage @fsx-lustre
  Scenario Outline: Configure Amazon FSx for Lustre - <storage_type> storage
    Given I search for "Amazon FSx for Lustre"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<storage_type>" from dropdown "Storage type"
    And I fill "Storage capacity" with "1200"
    And I fill "Backup storage" with "500"
    And I click Save and add service
    Then the service "Amazon FSx for Lustre" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Storage type variants
      | storage_type |
      | SSD          |
      | HDD          |

  @storage @fsx-ontap
  Scenario Outline: Configure Amazon FSx for NetApp ONTAP - <deployment>
    Given I search for "Amazon FSx for NetApp ONTAP"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<deployment>" from dropdown "Deployment type"
    And I fill "Desired storage capacity" with "1024"
    And I fill "Desired additional SSD IOPS" with "3000"
    And I fill "Desired aggregate throughput" with "512"
    And I fill "Backup storage" with "500"
    And I click Save and add service
    Then the service "Amazon FSx for NetApp ONTAP" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Deployment type variants
      | deployment             |
      | Single-AZ 1 Deployment |
      | Multi-AZ 1 Deployment  |
      | Single-AZ 2 Deployment |
      | Multi-AZ 2 Deployment  |

  @storage @fsx-openzfs
  Scenario: Configure Amazon FSx for OpenZFS with all fields
    Given I search for "Amazon FSx for OpenZFS"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Desired storage capacity" with "1024"
    And I click Save and add service
    Then the service "Amazon FSx for OpenZFS" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-windows
  Scenario: Configure Amazon FSx for Windows File Server with all fields
    Given I search for "Amazon FSx for Windows File Server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Desired storage capacity" with "1024"
    And I fill "Desired aggregate throughput" with "256"
    And I fill "Backup storage" with "500"
    And I click Save and add service
    Then the service "Amazon FSx for Windows File Server" should be added successfully
    And a shareable estimate URL should be generated

  @storage @file-cache
  Scenario: Configure Amazon File Cache with all fields
    Given I search for "Amazon File Cache"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Storage capacity" with "2400"
    And I click Save and add service
    Then the service "Amazon File Cache" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ecr
  Scenario: Configure Amazon Elastic Container Registry with all fields
    Given I search for "Amazon Elastic Container Registry"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Amount of data stored" with "50"
    And I fill "Enter Amount" with "500"
    And I click Save and add service
    Then the service "Amazon Elastic Container Registry" should be added successfully
    And a shareable estimate URL should be generated

  @storage @storage-gateway
  Scenario: Configure AWS Storage Gateway with all fields
    Given I search for "AWS Storage Gateway"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data written to AWS file storage by your gateway" with "500"
    And I fill "Enter Amount" with "100"
    And I click Save and add service
    Then the service "AWS Storage Gateway" should be added successfully
    And a shareable estimate URL should be generated

  @storage @backup
  Scenario: Configure AWS Backup with all fields
    Given I search for "AWS Backup"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Amount of primary data to be backed up" with "500"
    And I fill "Estimated daily change of primary data" with "5"
    And I fill "Daily backups warm retention period" with "30"
    And I fill "Weekly backups warm retention period" with "12"
    And I fill "Monthly backups warm retention period" with "12"
    And I click Save and add service
    Then the service "AWS Backup" should be added successfully
    And a shareable estimate URL should be generated

  @storage @snowball
  Scenario: Configure AWS Snowball with all fields
    Given I search for "AWS Snowball"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices" with "2"
    And I click Save and add service
    Then the service "AWS Snowball" should be added successfully
    And a shareable estimate URL should be generated

  @storage @datasync
  Scenario: Configure AWS DataSync with all fields
    Given I search for "AWS DataSync"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total data copied by AWS DataSync per month" with "1000"
    And I click Save and add service
    Then the service "AWS DataSync" should be added successfully
    And a shareable estimate URL should be generated

  @storage @elastic-disaster-recovery
  Scenario: Configure AWS Elastic Disaster Recovery with all fields
    Given I search for "AWS Elastic Disaster Recovery"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of source servers replicated per month" with "10"
    And I fill "Number of disks" with "20"
    And I fill "Storage on all disks and all servers" with "5000"
    And I fill "Number of days selected for EBS snapshot retention period" with "7"
    And I click Save and add service
    Then the service "AWS Elastic Disaster Recovery" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # NETWORKING & CONTENT DELIVERY
  # ============================================================

  @networking @cloudfront
  Scenario: Configure Amazon CloudFront with all fields
    Given I search for "Amazon CloudFront"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Free Plan" with "1"
    And I click Save and add service
    Then the service "Amazon CloudFront" should be added successfully
    And a shareable estimate URL should be generated

  @networking @vpc
  Scenario: Configure Amazon Virtual Private Cloud (VPC) - standard setup
    Given I search for "Amazon Virtual Private Cloud (VPC)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Instances" with "2"
    And I fill "Number of Site-to-Site VPN Connections" with "1"
    And I fill "Average duration for each connection" with "730"
    And I fill "Number of subnet associations" with "4"
    And I fill "Number of active Client VPN connections (or users)" with "10"
    And I fill "Working days per month" with "22"
    And I click Save and add service
    Then the service "Amazon Virtual Private Cloud (VPC)" should be added successfully
    And a shareable estimate URL should be generated

  @networking @vpc @enterprise
  Scenario: Configure Amazon Virtual Private Cloud (VPC) - enterprise setup
    Given I search for "Amazon Virtual Private Cloud (VPC)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Instances" with "10"
    And I fill "Number of Site-to-Site VPN Connections" with "4"
    And I fill "Average duration for each connection" with "730"
    And I fill "Number of subnet associations" with "16"
    And I fill "Number of active Client VPN connections (or users)" with "100"
    And I fill "Working days per month" with "22"
    And I click Save and add service
    Then the service "Amazon Virtual Private Cloud (VPC)" should be added successfully
    And a shareable estimate URL should be generated

  @networking @direct-connect
  Scenario: Configure AWS Direct Connect - standard
    Given I search for "AWS Direct Connect"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of ports" with "2"
    And I fill "Hours used" with "730"
    And I fill "Data transfer out" with "5000"
    And I fill "Data transfer in (free)" with "10000"
    And I click Save and add service
    Then the service "AWS Direct Connect" should be added successfully
    And a shareable estimate URL should be generated

  @networking @direct-connect @high-bandwidth
  Scenario: Configure AWS Direct Connect - high bandwidth
    Given I search for "AWS Direct Connect"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of ports" with "4"
    And I fill "Hours used" with "730"
    And I fill "Data transfer out" with "50000"
    And I fill "Data transfer in (free)" with "100000"
    And I click Save and add service
    Then the service "AWS Direct Connect" should be added successfully
    And a shareable estimate URL should be generated

  @networking @route53
  Scenario: Configure Amazon Route 53 - standard DNS
    Given I search for "Amazon Route 53"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Hosted Zones" with "5"
    And I fill "Additional Records in Hosted Zones" with "100"
    And I fill "Traffic Flow" with "2"
    And I fill "Standard queries" with "10000000"
    And I click Save and add service
    Then the service "Amazon Route 53" should be added successfully
    And a shareable estimate URL should be generated

  @networking @route53 @health-checks
  Scenario: Configure Amazon Route 53 - with health checks
    Given I search for "Amazon Route 53"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Hosted Zones" with "10"
    And I fill "Additional Records in Hosted Zones" with "500"
    And I fill "Traffic Flow" with "5"
    And I fill "Standard queries" with "50000000"
    And I fill "Basic Checks Within AWS" with "10"
    And I fill "HTTPS Checks Within AWS" with "5"
    And I fill "Number of domains stored" with "20"
    And I fill "DNS queries" with "1000000"
    And I click Save and add service
    Then the service "Amazon Route 53" should be added successfully
    And a shareable estimate URL should be generated

  @networking @elb
  Scenario: Configure Elastic Load Balancing - standard
    Given I search for "Elastic Load Balancing"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Application Load Balancers" with "2"
    And I fill "Processed bytes (Lambda functions as targets)" with "100"
    And I fill "Average number of new connections per ALB" with "100"
    And I fill "Average number of requests per second per ALB" with "500"
    And I fill "Average number of rule evaluations per request" with "10"
    And I click Save and add service
    Then the service "Elastic Load Balancing" should be added successfully
    And a shareable estimate URL should be generated

  @networking @elb @high-traffic
  Scenario: Configure Elastic Load Balancing - high traffic
    Given I search for "Elastic Load Balancing"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Application Load Balancers" with "10"
    And I fill "Processed bytes (Lambda functions as targets)" with "1000"
    And I fill "Average number of new connections per ALB" with "1000"
    And I fill "Average number of requests per second per ALB" with "5000"
    And I fill "Average number of rule evaluations per request" with "25"
    And I click Save and add service
    Then the service "Elastic Load Balancing" should be added successfully
    And a shareable estimate URL should be generated

  @networking @api-gateway
  Scenario: Configure Amazon API Gateway - REST API
    Given I search for "Amazon API Gateway"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Requests" with "10"
    And I fill "Average size of each request" with "3"
    And I click Save and add service
    Then the service "Amazon API Gateway" should be added successfully
    And a shareable estimate URL should be generated

  @networking @api-gateway @websocket
  Scenario: Configure Amazon API Gateway - WebSocket API
    Given I search for "Amazon API Gateway"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Requests" with "50"
    And I fill "Average size of each request" with "5"
    And I fill "Messages" with "10000"
    And I fill "Average message size" with "32"
    And I fill "Average connection rate" with "100"
    And I click Save and add service
    Then the service "Amazon API Gateway" should be added successfully
    And a shareable estimate URL should be generated

  @networking @data-transfer
  Scenario: Configure AWS Data Transfer with all fields
    Given I search for "AWS Data Transfer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Enter Amount" with "5000"
    And I click Save and add service
    Then the service "AWS Data Transfer" should be added successfully
    And a shareable estimate URL should be generated

  @networking @network-firewall
  Scenario: Configure AWS Network Firewall with all fields
    Given I search for "AWS Network Firewall"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of AWS Network Firewall endpoints" with "2"
    And I fill "Monthly usage per endpoint" with "730"
    And I fill "Advanced Inspection Monthly usage per endpoint" with "730"
    And I fill "Number of Network Firewall secondary endpoints" with "1"
    And I fill "Usage per secondary endpoint" with "730"
    And I fill "Data processed per month" with "1000"
    And I click Save and add service
    Then the service "AWS Network Firewall" should be added successfully
    And a shareable estimate URL should be generated

  @networking @waf
  Scenario: Configure AWS Web Application Firewall (WAF) with all fields
    Given I search for "AWS Web Application Firewall (WAF)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Web Access Control Lists (Web ACLs) utilized" with "3"
    And I fill "Number of Rules added per Web ACL" with "10"
    And I fill "Number of Rules inside each Rule Group" with "5"
    And I fill "Number of web requests received across all web ACLs" with "10000000"
    And I click Save and add service
    Then the service "AWS Web Application Firewall (WAF)" should be added successfully
    And a shareable estimate URL should be generated

  @networking @shield
  Scenario: Configure AWS Shield with all fields
    Given I search for "AWS Shield"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Cloud Front Usage" with "10"
    And I fill "Elastic Load Balancing (ELB) Usage" with "5"
    And I fill "Elastic IP Usage" with "3"
    And I fill "Global Accelerator Usage" with "2"
    And I click Save and add service
    Then the service "AWS Shield" should be added successfully
    And a shareable estimate URL should be generated

  @networking @firewall-manager
  Scenario: Configure AWS Firewall Manager with all fields
    Given I search for "AWS Firewall Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of protection policy" with "5"
    And I fill "Number of aws account" with "3"
    And I fill "Number of Configuration items recorded" with "1000"
    And I fill "Number of Config rule evaluations" with "5000"
    And I click Save and add service
    Then the service "AWS Firewall Manager" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # AI/ML SERVICES
  # ============================================================

  @ai-ml @bedrock
  Scenario Outline: Configure Amazon Bedrock - <inference_type> with <pricing>
    Given I search for "Amazon Bedrock"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<inference_type>" from dropdown "Inference type"
    And I select "<pricing>" from dropdown "Pricing model"
    And I fill "Average requests per minute" with "10"
    And I fill "Hours per day at this rate" with "8"
    And I fill "Average input tokens per request" with "500"
    And I fill "Average output tokens per request" with "200"
    And I click Save and add service
    Then the service "Amazon Bedrock" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Inference and pricing combinations
      | inference_type             | pricing              |
      | Geo Cross Region Inference | On Demand - Standard |
      | Geo Cross Region Inference | On Demand - Priority |
      | Geo Cross Region Inference | On Demand - Flex     |
      | Geo Cross Region Inference | Batch                |
      | In-Region                  | On Demand - Standard |
      | In-Region                  | Batch                |

  @ai-ml @bedrock-agentcore
  Scenario: Configure Amazon Bedrock AgentCore with all fields
    Given I search for "Amazon Bedrock AgentCore"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of agent sessions per month" with "10000"
    And I fill "Average Session Duration (seconds)" with "30"
    And I fill "Average vCPU excluding I/O wait time" with "2"
    And I fill "Average Session Memory (in GB)" with "4"
    And I click Save and add service
    Then the service "Amazon Bedrock AgentCore" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @sagemaker
  Scenario: Configure Amazon SageMaker - small team
    Given I search for "Amazon SageMaker"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of data scientist(s)" with "3"
    And I fill "Number of Studio Notebook instances per data scientist" with "1"
    And I fill "Studio Notebook hour(s) per day" with "8"
    And I fill "Studio Notebook day(s) per month" with "22"
    And I fill "Storage amount" with "50"
    And I click Save and add service
    Then the service "Amazon SageMaker" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @sagemaker @large-team
  Scenario: Configure Amazon SageMaker - large team
    Given I search for "Amazon SageMaker"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of data scientist(s)" with "15"
    And I fill "Number of Studio Notebook instances per data scientist" with "2"
    And I fill "Studio Notebook hour(s) per day" with "10"
    And I fill "Studio Notebook day(s) per month" with "22"
    And I fill "Number of On-Demand Notebook instances per data scientist" with "1"
    And I fill "On-Demand Notebook hour(s) per day" with "4"
    And I fill "On-Demand Notebook day(s) per month" with "22"
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon SageMaker" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @sagemaker-ground-truth
  Scenario: Configure Amazon SageMaker Ground Truth with all fields
    Given I search for "Amazon SageMaker Ground Truth"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of dataset objects" with "10000"
    And I fill "Number of workers per dataset object" with "3"
    And I fill "Number of human tasks per month" with "5000"
    And I click Save and add service
    Then the service "Amazon SageMaker Ground Truth" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @rekognition
  Scenario: Configure Amazon Rekognition with all fields
    Given I search for "Amazon Rekognition"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of images processed with labels API calls per month" with "100000"
    And I fill "Number of images processed with content moderation API calls per month" with "50000"
    And I fill "Number of images processed with detect text API calls per month" with "25000"
    And I fill "Number of DetectFaces API calls per month" with "10000"
    And I click Save and add service
    Then the service "Amazon Rekognition" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @comprehend
  Scenario: Configure Amazon Comprehend with all fields
    Given I search for "Amazon Comprehend"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of documents asynchronous" with "50000"
    And I fill "Average characters in a document asynchronous" with "2000"
    And I click Save and add service
    Then the service "Amazon Comprehend" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @comprehend-medical
  Scenario: Configure Amazon Comprehend Medical with all fields
    Given I search for "Amazon Comprehend Medical"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of text (utf-8) documents (NERe)" with "10000"
    And I fill "Average characters in a document (NERe)" with "5000"
    And I click Save and add service
    Then the service "Amazon Comprehend Medical" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @textract
  Scenario: Configure Amazon Textract with all fields
    Given I search for "Amazon Textract"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of pages" with "100000"
    And I fill "Percent of pages with text (Detect Document Text API) Enter %" with "80"
    And I click Save and add service
    Then the service "Amazon Textract" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @polly
  Scenario: Configure Amazon Polly with all fields
    Given I search for "Amazon Polly"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of requests (Standard Text-to-Speech)" with "50000"
    And I fill "Number of characters per request including white spaces, but excluding SSML" with "500"
    And I click Save and add service
    Then the service "Amazon Polly" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @translate
  Scenario: Configure Amazon Translate with all fields
    Given I search for "Amazon Translate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of characters including white spaces and punctuations (Standard Real-Time Translation)" with "10000000"
    And I click Save and add service
    Then the service "Amazon Translate" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @transcribe
  Scenario: Configure Amazon Transcribe with all fields
    Given I search for "Amazon Transcribe"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "Amazon Transcribe" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @transcribe-medical
  Scenario: Configure Amazon Transcribe Medical with all fields
    Given I search for "Amazon Transcribe Medical"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of minutes of medical audio transcription per month" with "10000"
    And I click Save and add service
    Then the service "Amazon Transcribe Medical" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @personalize
  Scenario: Configure Amazon Personalize with all fields
    Given I search for "Amazon Personalize"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "Amazon Personalize" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @forecast
  Scenario: Configure Amazon Forecast with all fields
    Given I search for "Amazon Forecast"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data imported" with "10"
    And I fill "Training hours" with "5"
    And I fill "Unique number of items" with "1000"
    And I fill "Number of forecast horizon data points" with "30"
    And I fill "Number of quantiles" with "3"
    And I fill "Forecasting frequency" with "12"
    And I click Save and add service
    Then the service "Amazon Forecast" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @fraud-detector
  Scenario: Configure Amazon Fraud Detector with all fields
    Given I search for "Amazon Fraud Detector"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Event data processed and stored" with "10"
    And I fill "Number of model versions" with "2"
    And I fill "Training time per model version in hours" with "4"
    And I fill "Number of active model versions" with "1"
    And I click Save and add service
    Then the service "Amazon Fraud Detector" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @kendra
  Scenario: Configure Amazon Kendra with all fields
    Given I search for "Amazon Kendra"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "Amazon Kendra" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @augmented-ai
  Scenario: Configure Amazon Augmented AI with all fields
    Given I search for "Amazon Augmented AI"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of reviewed images per month with Amazon Rekognition and Amazon Augmented AI" with "5000"
    And I fill "Number of reviewed pages per month with Amazon Textract and Amazon Augmented AI" with "3000"
    And I fill "Number of reviewed objects per month with a Custom Model and Amazon Augmented AI" with "2000"
    And I click Save and add service
    Then the service "Amazon Augmented AI" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @lookout-metrics
  Scenario: Configure Amazon Lookout for Metrics with all fields
    Given I search for "Amazon Lookout for Metrics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of measures" with "100"
    And I fill "Total number of dimension values" with "500"
    And I click Save and add service
    Then the service "Amazon Lookout for Metrics" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @lookout-vision
  Scenario: Configure Amazon Lookout for Vision with all fields
    Given I search for "Amazon Lookout for Vision"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of plants" with "1"
    And I fill "Number of production lines per plant" with "3"
    And I fill "Number of inspection points per production line" with "2"
    And I fill "Number of cameras per inspection point" with "1"
    And I fill "Time to train initial model (hours)" with "4"
    And I fill "Number of inference units" with "2"
    And I click Save and add service
    Then the service "Amazon Lookout for Vision" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @entity-resolution
  Scenario: Configure AWS Entity Resolution with all fields
    Given I search for "AWS Entity Resolution"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Records" with "1000000"
    And I click Save and add service
    Then the service "AWS Entity Resolution" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # ANALYTICS SERVICES
  # ============================================================

  @analytics @athena
  Scenario: Configure Amazon Athena - on-demand queries
    Given I search for "Amazon Athena"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of queries" with "1000"
    And I fill "Amount of data scanned per query" with "5"
    And I click Save and add service
    Then the service "Amazon Athena" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @athena @provisioned
  Scenario: Configure Amazon Athena - provisioned capacity
    Given I search for "Amazon Athena"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of queries" with "5000"
    And I fill "Amount of data scanned per query" with "10"
    And I fill "Number of DPUs" with "8"
    And I fill "Length of time capacity is active" with "200"
    And I fill "Total number of spark sessions" with "50"
    And I fill "Code execution per session" with "30"
    And I click Save and add service
    Then the service "Amazon Athena" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @kinesis-data-streams
  Scenario: Configure Amazon Kinesis Data Streams - standard
    Given I search for "Amazon Kinesis Data Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of records" with "100000"
    And I fill "Average record size" with "5"
    And I fill "Number of Consumer Applications" with "2"
    And I fill "Number of days for data retention" with "7"
    And I fill "Number of Enhanced fan-out consumers" with "1"
    And I click Save and add service
    Then the service "Amazon Kinesis Data Streams" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @kinesis-data-streams @high-throughput
  Scenario: Configure Amazon Kinesis Data Streams - high throughput
    Given I search for "Amazon Kinesis Data Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of records" with "5000000"
    And I fill "Average record size" with "10"
    And I fill "Number of Consumer Applications" with "5"
    And I fill "Number of days for data retention" with "30"
    And I fill "Number of Enhanced fan-out consumers" with "3"
    And I click Save and add service
    Then the service "Amazon Kinesis Data Streams" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @kinesis-video
  Scenario: Configure Amazon Kinesis Video Streams with all fields
    Given I search for "Amazon Kinesis Video Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices" with "10"
    And I fill "Average bitrate" with "5"
    And I fill "Duration of video streamed to Amazon Kinesis Video Streams (per device)" with "8"
    And I fill "Average retention for video" with "24"
    And I click Save and add service
    Then the service "Amazon Kinesis Video Streams" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @data-firehose
  Scenario Outline: Configure Amazon Data firehose - <source> source
    Given I search for "Amazon Data firehose"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<source>" from dropdown "Source"
    And I fill "Number of records for data ingestion" with "1000"
    And I fill "Record size" with "5"
    And I click Save and add service
    Then the service "Amazon Data firehose" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Source variants
      | source                               |
      | Direct PUT or Kinesis Data Stream     |
      | Vended logs                           |
      | MSK or MSK Serverless                 |

  @analytics @msk
  Scenario: Configure Amazon Managed Streaming for Apache Kafka (MSK) - small
    Given I search for "Amazon Managed Streaming for Apache Kafka (MSK)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Kafka broker nodes" with "3"
    And I select "kafka.m5.large" via autosuggest for "Select an instance"
    And I fill "Storage per Broker" with "500"
    And I click Save and add service
    Then the service "Amazon Managed Streaming for Apache Kafka (MSK)" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @msk @large
  Scenario: Configure Amazon Managed Streaming for Apache Kafka (MSK) - large
    Given I search for "Amazon Managed Streaming for Apache Kafka (MSK)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Kafka broker nodes" with "9"
    And I select "kafka.m5.2xlarge" via autosuggest for "Select an instance"
    And I fill "Storage per Broker" with "2000"
    And I fill "Desired Provisioned Storage Throughput (MiBps)" with "500"
    And I click Save and add service
    Then the service "Amazon Managed Streaming for Apache Kafka (MSK)" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @managed-flink
  Scenario: Configure Amazon Managed Service for Apache Flink with all fields
    Given I search for "Amazon Managed Service for Apache Flink"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Apache Flink applications" with "2"
    And I fill "Apache Flink KPUs" with "4"
    And I fill "Durable application backups maintained" with "3"
    And I fill "Durable application backup storage (average size)" with "10"
    And I click Save and add service
    Then the service "Amazon Managed Service for Apache Flink" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @glue
  Scenario: Configure AWS Glue - Spark ETL
    Given I search for "AWS Glue"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of DPUs for Apache Spark job" with "10"
    And I fill "Duration for which Apache Spark ETL job  runs" with "2"
    And I fill "Number of DPUs for Python Shell job" with "2"
    And I fill "Number of DPUs for each provisioned interactive session" with "5"
    And I click Save and add service
    Then the service "AWS Glue" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @glue @heavy-etl
  Scenario: Configure AWS Glue - heavy ETL workload
    Given I search for "AWS Glue"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of DPUs for Apache Spark job" with "50"
    And I fill "Duration for which Apache Spark ETL job  runs" with "8"
    And I fill "Number of DPUs for Python Shell job" with "10"
    And I fill "Number of DPUs for each provisioned interactive session" with "20"
    And I click Save and add service
    Then the service "AWS Glue" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @lake-formation
  Scenario: Configure AWS Lake Formation with all fields
    Given I search for "AWS Lake Formation"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data scanned" with "100"
    And I fill "Storage usage in a month (in millions)" with "5"
    And I fill "Requests in a month (in millions)" with "10"
    And I fill "Number of tables" with "50"
    And I click Save and add service
    Then the service "AWS Lake Formation" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @quicksight
  Scenario: Configure Amazon QuickSight with all fields
    Given I search for "Amazon QuickSight"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Readers" with "100"
    And I fill "Number of Authors" with "10"
    And I click Save and add service
    Then the service "Amazon QuickSight" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @finspace
  Scenario: Configure Amazon FinSpace Dataset Browser with all fields
    Given I search for "Amazon FinSpace Dataset Browser"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of users" with "5"
    And I fill "Size of data to be stored" with "100"
    And I fill "Total time spent: Small cluster (across all users)" with "40"
    And I fill "Total time spent: Medium cluster (across all users)" with "20"
    And I click Save and add service
    Then the service "Amazon FinSpace Dataset Browser" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # APPLICATION INTEGRATION
  # ============================================================

  @integration @sqs
  Scenario: Configure Amazon Simple Queue Service (SQS) - standard workload
    Given I search for "Amazon Simple Queue Service (SQS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Standard queue requests" with "10000000"
    And I fill "FIFO queue requests" with "1000000"
    And I fill "Fair queue requests" with "500000"
    And I click Save and add service
    Then the service "Amazon Simple Queue Service (SQS)" should be added successfully
    And a shareable estimate URL should be generated

  @integration @sqs @high-throughput
  Scenario: Configure Amazon Simple Queue Service (SQS) - high throughput
    Given I search for "Amazon Simple Queue Service (SQS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Standard queue requests" with "100000000"
    And I fill "FIFO queue requests" with "50000000"
    And I fill "Fair queue requests" with "10000000"
    And I fill "Enter Amount" with "5000"
    And I click Save and add service
    Then the service "Amazon Simple Queue Service (SQS)" should be added successfully
    And a shareable estimate URL should be generated

  @integration @sns
  Scenario: Configure Amazon Simple Notification Service (SNS) with all fields
    Given I search for "Amazon Simple Notification Service (SNS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Requests" with "10000000"
    And I fill "HTTP/HTTPS Notifications" with "5000000"
    And I fill "EMAIL/EMAIL-JSON Notifications" with "100000"
    And I fill "SQS Notifications" with "2000000"
    And I click Save and add service
    Then the service "Amazon Simple Notification Service (SNS)" should be added successfully
    And a shareable estimate URL should be generated

  @integration @eventbridge
  Scenario: Configure Amazon EventBridge - standard events
    Given I search for "Amazon EventBridge"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of the payload" with "10"
    And I fill "Number of AWS management events" with "1000000"
    And I fill "Number of custom events" with "5000000"
    And I fill "Number of invocations" with "2000000"
    And I click Save and add service
    Then the service "Amazon EventBridge" should be added successfully
    And a shareable estimate URL should be generated

  @integration @eventbridge @cross-account
  Scenario: Configure Amazon EventBridge - cross-account with pipes
    Given I search for "Amazon EventBridge"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of the payload" with "64"
    And I fill "Number of custom events" with "20000000"
    And I fill "Number of partner events" with "5000000"
    And I fill "Number of events delivered to another event bus" with "10000000"
    And I fill "Number of events delivered to a service in a different account" with "5000000"
    And I fill "Number of invocations" with "10000000"
    And I fill "Number of replayed events" with "1000000"
    And I click Save and add service
    Then the service "Amazon EventBridge" should be added successfully
    And a shareable estimate URL should be generated

  @integration @swf
  Scenario: Configure Amazon Simple Workflow Service (SWF) with all fields
    Given I search for "Amazon Simple Workflow Service (SWF)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Workflow Executions" with "10000"
    And I fill "Total Tasks, Markers, Timers and Signals" with "50000"
    And I fill "Workflow lifetime" with "30"
    And I fill "Workflow retention" with "90"
    And I click Save and add service
    Then the service "Amazon Simple Workflow Service (SWF)" should be added successfully
    And a shareable estimate URL should be generated

  @integration @appflow
  Scenario: Configure Amazon AppFlow with all fields
    Given I search for "Amazon AppFlow"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of flows" with "5"
    And I fill "Volume of data per flow" with "10"
    And I click Save and add service
    Then the service "Amazon AppFlow" should be added successfully
    And a shareable estimate URL should be generated

  @integration @appsync
  Scenario: Configure AWS AppSync with all fields
    Given I search for "AWS AppSync"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of API Requests" with "5000000"
    And I fill "Enter Amount" with "500"
    And I click Save and add service
    Then the service "AWS AppSync" should be added successfully
    And a shareable estimate URL should be generated

  @integration @mq
  Scenario Outline: Configure Amazon MQ - <broker_type> with <storage>
    Given I search for "Amazon MQ"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<broker_type>" from dropdown "Broker type"
    And I select "<instance_type>" from dropdown "Instance type"
    And I select "<storage>" from dropdown "Storage type"
    And I fill "Number of Brokers running" with "2"
    And I fill "Storage per Broker" with "50"
    And I click Save and add service
    Then the service "Amazon MQ" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Broker and storage combinations
      | broker_type                    | instance_type  | storage                           |
      | Single-instance Broker         | mq.m5.large    | Durability optimized (Amazon EFS) |
      | Single-instance Broker         | mq.t3.micro    | Throughput optimized (EBS)        |
      | Single-instance Broker         | mq.m5.xlarge   | Throughput optimized (EBS)        |
      | Active/standby-instance Broker | mq.m5.large    | Durability optimized (Amazon EFS) |
      | Active/standby-instance Broker | mq.m5.xlarge   | Durability optimized (Amazon EFS) |
      | Active/standby-instance Broker | mq.m5.2xlarge  | Throughput optimized (EBS)        |

  # ============================================================
  # MESSAGING & COMMUNICATION
  # ============================================================

  @messaging @ses
  Scenario: Configure Amazon Simple Email Service (SES) with all fields
    Given I search for "Amazon Simple Email Service (SES)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Open Ingress Endpoint(s)" with "1"
    And I fill "Number of Emails processed by Mail Manager" with "100000"
    And I fill "Email messages sent from EC2" with "50000"
    And I fill "Attachment data sent from EC2" with "100"
    And I click Save and add service
    Then the service "Amazon Simple Email Service (SES)" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @pinpoint
  Scenario: Configure Amazon Pinpoint with all fields
    Given I search for "Amazon Pinpoint"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of push notifications" with "1000000"
    And I fill "Number of in-app message requests" with "500000"
    And I click Save and add service
    Then the service "Amazon Pinpoint" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # MANAGEMENT & GOVERNANCE
  # ============================================================

  @management @cloudwatch
  Scenario: Configure Amazon CloudWatch - standard monitoring
    Given I search for "Amazon CloudWatch"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Metrics (includes detailed and custom metrics)" with "500"
    And I fill "GetMetricData: Number of metrics requested" with "1000"
    And I fill "Number of other API requests" with "100000"
    And I click Save and add service
    Then the service "Amazon CloudWatch" should be added successfully
    And a shareable estimate URL should be generated

  @management @cloudwatch @database-insights
  Scenario: Configure Amazon CloudWatch - with database insights
    Given I search for "Amazon CloudWatch"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Metrics (includes detailed and custom metrics)" with "2000"
    And I fill "GetMetricData: Number of metrics requested" with "5000"
    And I fill "GetMetricWidgetImage: Number of metrics requested" with "1000"
    And I fill "Number of other API requests" with "500000"
    And I fill "Number of vCPUs monitored by Database Insights" with "32"
    And I click Save and add service
    Then the service "Amazon CloudWatch" should be added successfully
    And a shareable estimate URL should be generated

  @management @cloudtrail
  Scenario: Configure AWS CloudTrail with all fields
    Given I search for "AWS CloudTrail"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of management events" with "1000000"
    And I fill "Management event trails" with "2"
    And I fill "Data ingested - CloudTrail" with "100"
    And I fill "Data scanned using queries" with "50"
    And I click Save and add service
    Then the service "AWS CloudTrail" should be added successfully
    And a shareable estimate URL should be generated

  @management @config
  Scenario: Configure AWS Config with all fields
    Given I search for "AWS Config"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Continuous Configuration items recorded" with "5000"
    And I fill "Number of Periodic Configuration items recorded" with "1000"
    And I fill "Number of Config rule evaluations" with "10000"
    And I fill "Number of Conformance pack evaluations" with "5000"
    And I click Save and add service
    Then the service "AWS Config" should be added successfully
    And a shareable estimate URL should be generated

  @management @cloudformation
  Scenario: Configure AWS CloudFormation with all fields
    Given I search for "AWS CloudFormation"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of third-party extensions managed" with "5"
    And I fill "Total number of operations per extension" with "100"
    And I click Save and add service
    Then the service "AWS CloudFormation" should be added successfully
    And a shareable estimate URL should be generated

  @management @systems-manager
  Scenario: Configure AWS Systems Manager with all fields
    Given I search for "AWS Systems Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Standard parameters" with "100"
    And I fill "Advanced parameters" with "10"
    And I fill "Frequency of API interactions per parameter" with "1000"
    And I click Save and add service
    Then the service "AWS Systems Manager" should be added successfully
    And a shareable estimate URL should be generated

  @management @service-catalog
  Scenario: Configure AWS Service Catalog with all fields
    Given I search for "AWS Service Catalog"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of API calls" with "10000"
    And I click Save and add service
    Then the service "AWS Service Catalog" should be added successfully
    And a shareable estimate URL should be generated

  @management @managed-grafana
  Scenario: Configure Amazon Managed Grafana with all fields
    Given I search for "Amazon Managed Grafana"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of active editors/administrators" with "5"
    And I fill "Number of active viewers" with "20"
    And I click Save and add service
    Then the service "Amazon Managed Grafana" should be added successfully
    And a shareable estimate URL should be generated

  @management @managed-prometheus
  Scenario: Configure Amazon Managed Service for Prometheus with all fields
    Given I search for "Amazon Managed Service for Prometheus"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average active time series" with "100000"
    And I fill "Avg Collection Interval (in seconds)" with "60"
    And I fill "Retention Period (in days)" with "90"
    And I fill "Average Number of Dashboard users per day" with "5"
    And I click Save and add service
    Then the service "Amazon Managed Service for Prometheus" should be added successfully
    And a shareable estimate URL should be generated

  @management @xray
  Scenario: Configure AWS X-Ray with all fields
    Given I search for "AWS X-Ray"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of requests per month" with "5000000"
    And I fill "Number of queries per month" with "10000"
    And I fill "Traces retrieved per query" with "100"
    And I click Save and add service
    Then the service "AWS X-Ray" should be added successfully
    And a shareable estimate URL should be generated

  @management @resilience-hub
  Scenario: Configure AWS Resilience Hub with all fields
    Given I search for "AWS Resilience Hub"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of applications assessed for resilience" with "10"
    And I click Save and add service
    Then the service "AWS Resilience Hub" should be added successfully
    And a shareable estimate URL should be generated

  @management @fis
  Scenario: Configure AWS Fault Injection Service (FIS) with all fields
    Given I search for "AWS Fault Injection Service (FIS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Experiments per Month" with "20"
    And I fill "Average action-minutes per experiment" with "30"
    And I fill "Average count of target accounts per experiment" with "2"
    And I click Save and add service
    Then the service "AWS Fault Injection Service (FIS)" should be added successfully
    And a shareable estimate URL should be generated

  @management @audit-manager
  Scenario: Configure AWS Audit Manager with all fields
    Given I search for "AWS Audit Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of accounts" with "5"
    And I fill "Number of resources per account" with "200"
    And I fill "Number of configuration snapshots (API calls)" with "1000"
    And I click Save and add service
    Then the service "AWS Audit Manager" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # SECURITY, IDENTITY & COMPLIANCE
  # ============================================================

  @security @guardduty
  Scenario: Configure Amazon GuardDuty - basic protection
    Given I search for "Amazon GuardDuty"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "AWS CloudTrail Management Event Analysis" with "5000000"
    And I fill "EC2 VPC Flow Log Analysis" with "100"
    And I fill "EC2 DNS Query Log Analysis" with "50"
    And I fill "AWS CloudTrail S3 Data Event Analysis" with "10000000"
    And I click Save and add service
    Then the service "Amazon GuardDuty" should be added successfully
    And a shareable estimate URL should be generated

  @security @guardduty @full-protection
  Scenario: Configure Amazon GuardDuty - full protection suite
    Given I search for "Amazon GuardDuty"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "AWS CloudTrail Management Event Analysis" with "10000000"
    And I fill "EC2 VPC Flow Log Analysis" with "500"
    And I fill "EC2 DNS Query Log Analysis" with "200"
    And I fill "AWS CloudTrail S3 Data Event Analysis" with "50000000"
    And I fill "Amazon EKS Audit Logs Analysis" with "100"
    And I fill "EBS Volume Data Scan Analysis" with "500"
    And I fill "RDS provisioned instance vCPU" with "64"
    And I fill "Lambda VPC Flow Log Analysis" with "100"
    And I click Save and add service
    Then the service "Amazon GuardDuty" should be added successfully
    And a shareable estimate URL should be generated

  @security @inspector
  Scenario: Configure Amazon Inspector - standard scanning
    Given I search for "Amazon Inspector"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average* No. of EC2 instances scanned per month" with "50"
    And I fill "Total number of newly pushed container images per month" with "100"
    And I fill "Total number of automated rescans per image per month" with "4"
    And I fill "Average number of Lambda functions scanned in a month" with "25"
    And I click Save and add service
    Then the service "Amazon Inspector" should be added successfully
    And a shareable estimate URL should be generated

  @security @inspector @code-scanning
  Scenario: Configure Amazon Inspector - with code scanning
    Given I search for "Amazon Inspector"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average* No. of EC2 instances scanned per month" with "200"
    And I fill "Total number of newly pushed container images per month" with "500"
    And I fill "Total number of automated rescans per image per month" with "8"
    And I fill "Average number of Lambda functions scanned in a month" with "100"
    And I fill "Total number of repositories" with "50"
    And I fill "Number of SAST periodic scans per repository per month" with "30"
    And I click Save and add service
    Then the service "Amazon Inspector" should be added successfully
    And a shareable estimate URL should be generated

  @security @macie
  Scenario: Configure Amazon Macie with all fields
    Given I search for "Amazon Macie"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of S3 buckets" with "50"
    And I fill "Total bytes in S3 storage" with "1000"
    And I fill "Number of objects monitored for automated data discovery" with "10000000"
    And I click Save and add service
    Then the service "Amazon Macie" should be added successfully
    And a shareable estimate URL should be generated

  @security @detective
  Scenario: Configure Amazon Detective with all fields
    Given I search for "Amazon Detective"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data ingested from AWS CloudTrail, Amazon VPC Flow Logs, Amazon GuardDuty (per account, per region)" with "100"
    And I click Save and add service
    Then the service "Amazon Detective" should be added successfully
    And a shareable estimate URL should be generated

  @security @security-hub
  Scenario: Configure AWS Security Hub with all fields
    Given I search for "AWS Security Hub"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Accounts" with "5"
    And I fill "Number of Security Checks per Account" with "500"
    And I fill "Number of Finding Ingested per Account" with "10000"
    And I fill "Number of Automation Rules" with "10"
    And I click Save and add service
    Then the service "AWS Security Hub" should be added successfully
    And a shareable estimate URL should be generated

  @security @kms
  Scenario: Configure AWS Key Management Service with all fields
    Given I search for "AWS Key Management Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of customer managed Customer Master Keys (CMK)" with "10"
    And I fill "Number of symmetric requests" with "1000000"
    And I fill "Number of asymmetric requests except RSA 2048" with "100000"
    And I fill "Number of asymmetric requests involving RSA 2048" with "50000"
    And I click Save and add service
    Then the service "AWS Key Management Service" should be added successfully
    And a shareable estimate URL should be generated

  @security @secrets-manager
  Scenario: Configure AWS Secrets Manager with all fields
    Given I search for "AWS Secrets Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of secrets" with "100"
    And I fill "Average duration of each secret" with "30"
    And I fill "Number of API calls" with "500000"
    And I click Save and add service
    Then the service "AWS Secrets Manager" should be added successfully
    And a shareable estimate URL should be generated

  @security @certificate-manager
  Scenario: Configure AWS Certificate Manager with all fields
    Given I search for "AWS Certificate Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of fully qualified domain names (FQDNs)" with "10"
    And I fill "Number of wildcard domain names" with "3"
    And I fill "Number of API calls" with "1000"
    And I click Save and add service
    Then the service "AWS Certificate Manager" should be added successfully
    And a shareable estimate URL should be generated

  @security @private-ca
  Scenario: Configure AWS Private Certificate Authority with all fields
    Given I search for "AWS Private Certificate Authority"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Private CAs" with "2"
    And I fill "Number of general purpose mode private certificates issued" with "1000"
    And I fill "Number of certificates used with ACM-integrated services" with "500"
    And I click Save and add service
    Then the service "AWS Private Certificate Authority" should be added successfully
    And a shareable estimate URL should be generated

  @security @cloudhsm
  Scenario: Configure AWS CloudHSM with all fields
    Given I search for "AWS CloudHSM"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of hsm1.medium HSMs" with "2"
    And I fill "Total number of hsm2m.medium HSMs" with "1"
    And I click Save and add service
    Then the service "AWS CloudHSM" should be added successfully
    And a shareable estimate URL should be generated

  @security @iam-access-analyzer
  Scenario: Configure AWS IAM Access Analyzer with all fields
    Given I search for "AWS IAM Access Analyzer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of accounts to monitor" with "5"
    And I fill "Average roles per account" with "50"
    And I fill "Average users per account" with "100"
    And I fill "Number of analyzers per account" with "2"
    And I click Save and add service
    Then the service "AWS IAM Access Analyzer" should be added successfully
    And a shareable estimate URL should be generated

  @security @cognito
  Scenario: Configure Amazon Cognito with all fields
    Given I search for "Amazon Cognito"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of monthly active users (MAU)" with "50000"
    And I fill "Number of monthly active users (MAU) who sign in through SAML or OIDC federation" with "5000"
    And I fill "Number of token requests" with "100000"
    And I fill "Number of app clients" with "5"
    And I click Save and add service
    Then the service "Amazon Cognito" should be added successfully
    And a shareable estimate URL should be generated

  @security @verified-permissions
  Scenario: Configure Amazon Verified Permissions with all fields
    Given I search for "Amazon Verified Permissions"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Single Authorization Requests" with "1000000"
    And I fill "Number of Batch Authorization Requests" with "100000"
    And I fill "Number of Policy Management Requests" with "10000"
    And I click Save and add service
    Then the service "Amazon Verified Permissions" should be added successfully
    And a shareable estimate URL should be generated

  @security @security-lake
  Scenario: Configure Amazon Security Lake with all fields
    Given I search for "Amazon Security Lake"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "CloudTrail events" with "10000000"
    And I click Save and add service
    Then the service "Amazon Security Lake" should be added successfully
    And a shareable estimate URL should be generated

  @security @payment-cryptography
  Scenario: Configure AWS Payment Cryptography with all fields
    Given I search for "AWS Payment Cryptography"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of API requests" with "1000000"
    And I fill "Number of active keys" with "10"
    And I click Save and add service
    Then the service "AWS Payment Cryptography" should be added successfully
    And a shareable estimate URL should be generated

  @security @directory-service
  Scenario: Configure AWS Directory Service with all fields
    Given I search for "AWS Directory Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of directories" with "2"
    And I fill "Number of total additional domain controllers" with "2"
    And I fill "Number of directories to be shared" with "1"
    And I fill "Number of additional accounts to which each directory is shared" with "3"
    And I click Save and add service
    Then the service "AWS Directory Service" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # DEVELOPER TOOLS
  # ============================================================

  @developer @codebuild
  Scenario: Configure AWS CodeBuild with all fields
    Given I search for "AWS CodeBuild"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of builds in a month" with "500"
    And I fill "Average build duration (minutes)" with "10"
    And I select "general1.medium" via autosuggest for "Select an instance"
    And I click Save and add service
    Then the service "AWS CodeBuild" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codedeploy
  Scenario: Configure AWS CodeDeploy with all fields
    Given I search for "AWS CodeDeploy"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of on-premise instances" with "10"
    And I fill "Number of deployments" with "50"
    And I click Save and add service
    Then the service "AWS CodeDeploy" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codepipeline
  Scenario: Configure AWS CodePipeline with all fields
    Given I search for "AWS CodePipeline"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of active pipelines of type V1 used per account per month" with "5"
    And I fill "Number of action execution minutes used in pipeline of type V2 per account per month" with "1000"
    And I click Save and add service
    Then the service "AWS CodePipeline" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codeartifact
  Scenario: Configure AWS CodeArtifact with all fields
    Given I search for "AWS CodeArtifact"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of artifacts stored" with "50"
    And I fill "Number of API requests" with "100000"
    And I fill "Enter Amount" with "200"
    And I click Save and add service
    Then the service "AWS CodeArtifact" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codeguru
  Scenario: Configure Amazon CodeGuru Reviewer with all fields
    Given I search for "Amazon CodeGuru Reviewer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of repositories" with "10"
    And I fill "Average lines of code (LOC) per repository" with "50000"
    And I click Save and add service
    Then the service "Amazon CodeGuru Reviewer" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # IOT SERVICES
  # ============================================================

  @iot @iot-core
  Scenario: Configure AWS IoT Core - small deployment
    Given I search for "AWS IoT Core"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices (MQTT)" with "10000"
    And I click Save and add service
    Then the service "AWS IoT Core" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-core @large
  Scenario: Configure AWS IoT Core - large fleet
    Given I search for "AWS IoT Core"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices (MQTT)" with "500000"
    And I click Save and add service
    Then the service "AWS IoT Core" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-analytics
  Scenario: Configure AWS IoT Analytics with all fields
    Given I search for "AWS IoT Analytics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of IoT devices (monthly)" with "1000"
    And I fill "Data generation by each device" with "10"
    And I fill "Number of data pipelines (monthly)" with "5"
    And I fill "Data queried per month" with "100"
    And I click Save and add service
    Then the service "AWS IoT Analytics" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-events
  Scenario: Configure AWS IoT Events with all fields
    Given I search for "AWS IoT Events"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices" with "500"
    And I fill "Number of messages for a device including timer expiry messages" with "100"
    And I fill "Number of event detector models per device" with "2"
    And I fill "Average size of each message" with "1"
    And I click Save and add service
    Then the service "AWS IoT Events" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-greengrass
  Scenario: Configure AWS IoT Greengrass with all fields
    Given I search for "AWS IoT Greengrass"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of greengrass core devices" with "50"
    And I fill "Activity Period in minutes per month" with "43200"
    And I fill "MQTT topics with cloud as source (optional)" with "10"
    And I click Save and add service
    Then the service "AWS IoT Greengrass" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-sitewise
  Scenario: Configure AWS IoT SiteWise with all fields
    Given I search for "AWS IoT SiteWise"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of daily measurements" with "1000000"
    And I fill "Number of tags or sensors" with "500"
    And I fill "Cloud data availablity" with "30"
    And I fill "Buffer period" with "7"
    And I click Save and add service
    Then the service "AWS IoT SiteWise" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-device-defender
  Scenario: Configure AWS IoT Device Defender with all fields
    Given I search for "AWS IoT Device Defender"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "AWS IoT Device Defender" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-device-management
  Scenario: Configure AWS IoT Device Management with all fields
    Given I search for "AWS IoT Device Management"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "AWS IoT Device Management" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # MEDIA SERVICES
  # ============================================================

  @media @medialive
  Scenario: Configure AWS Elemental MediaLive with all fields
    Given I search for "AWS Elemental MediaLive"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of inputs" with "2"
    And I fill "Active hours (On Demand)" with "730"
    And I fill "Number of outputs" with "4"
    And I click Save and add service
    Then the service "AWS Elemental MediaLive" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediaconvert
  Scenario: Configure AWS Elemental MediaConvert with all fields
    Given I search for "AWS Elemental MediaConvert"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Output basic usage" with "1000"
    And I click Save and add service
    Then the service "AWS Elemental MediaConvert" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediapackage
  Scenario: Configure AWS Elemental MediaPackage with all fields
    Given I search for "AWS Elemental MediaPackage"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of inputs per channel" with "2"
    And I fill "Total duration of live streams per month" with "730"
    And I fill "Ingest bitrate per input (Mbit per second)" with "5"
    And I fill "Average Number of viewers per hour" with "1000"
    And I click Save and add service
    Then the service "AWS Elemental MediaPackage" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediaconnect
  Scenario: Configure AWS Elemental MediaConnect with all fields
    Given I search for "AWS Elemental MediaConnect"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of running flows" with "2"
    And I fill "Flow utilization" with "730"
    And I fill "Number of outputs per flow" with "3"
    And I fill "Bitrate (Mbit per second)" with "10"
    And I click Save and add service
    Then the service "AWS Elemental MediaConnect" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediatailor
  Scenario: Configure AWS Elemental Media Tailor with all fields
    Given I search for "AWS Elemental Media Tailor"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Basic tier channel hours per month" with "730"
    And I fill "Standard tier channel hours per month" with "730"
    And I click Save and add service
    Then the service "AWS Elemental Media Tailor" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # MIGRATION & TRANSFER
  # ============================================================

  @migration @dms
  Scenario: Configure AWS Database Migration Service with all fields
    Given I search for "AWS Database Migration Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of instances" with "2"
    And I select "dms.r5.large" via autosuggest for "Select an instance"
    And I fill "Storage amount (multiple AZ)" with "200"
    And I click Save and add service
    Then the service "AWS Database Migration Service" should be added successfully
    And a shareable estimate URL should be generated

  @migration @application-migration
  Scenario: Configure AWS Application Migration Service with all fields
    Given I search for "AWS Application Migration Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of server/s" with "10"
    And I fill "Number of hour/s per server" with "730"
    And I click Save and add service
    Then the service "AWS Application Migration Service" should be added successfully
    And a shareable estimate URL should be generated

  @migration @transfer-family
  Scenario: Configure AWS Transfer Family with all fields
    Given I search for "AWS Transfer Family"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of endpoints with AS2 enabled" with "2"
    And I fill "Number of AS2 messages sent per month" with "10000"
    And I fill "Number of AS2 messages received per month" with "10000"
    And I click Save and add service
    Then the service "AWS Transfer Family" should be added successfully
    And a shareable estimate URL should be generated

  @migration @migration-hub-refactor
  Scenario: Configure AWS Migration Hub Refactor Spaces with all fields
    Given I search for "AWS Migration Hub Refactor Spaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Environments" with "2"
    And I fill "Number of Hours" with "730"
    And I fill "API Requests" with "100000"
    And I click Save and add service
    Then the service "AWS Migration Hub Refactor Spaces" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # BUSINESS APPLICATIONS
  # ============================================================

  @business @workspaces
  Scenario Outline: Configure Amazon WorkSpaces - <os>
    Given I search for "Amazon WorkSpaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<os>" from dropdown "Operating system"
    And I fill "Number of WorkSpaces" with "10"
    And I fill "Billing option" with "730"
    And I click Save and add service
    Then the service "Amazon WorkSpaces" should be added successfully
    And a shareable estimate URL should be generated

    Examples: OS variants
      | os                       |
      | Windows                  |
      | Red Hat Enterprise Linux |
      | Ubuntu Linux             |
      | Rocky Linux              |

  @business @workspaces @high-performance
  Scenario: Configure Amazon WorkSpaces with high-performance bundle
    Given I search for "Amazon WorkSpaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Windows" from dropdown "Operating system"
    And I fill "Number of WorkSpaces" with "25"
    And I fill "Billing option" with "730"
    And I click Save and add service
    Then the service "Amazon WorkSpaces" should be added successfully
    And a shareable estimate URL should be generated

  @business @workspaces-applications
  Scenario: Configure Amazon WorkSpaces Applications with all fields
    Given I search for "Amazon WorkSpaces Applications"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of users per month" with "50"
    And I fill "Number of working hours per day" with "8"
    And I fill "Instance Disk Volume size" with "100"
    And I fill "Days in week" with "5"
    And I select "stream.standard.large" via autosuggest for "Select an instance"
    And I click Save and add service
    Then the service "Amazon WorkSpaces Applications" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # WORKFLOW & ORCHESTRATION
  # ============================================================

  @workflow @managed-airflow
  Scenario Outline: Configure Amazon Managed Workflows for Apache Airflow - <env_size> environment
    Given I search for "Amazon Managed Workflows for Apache Airflow"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "<env_size>" from dropdown "Environment size"
    And I fill "Minimum workers" with "2"
    And I fill "Maximum workers" with "10"
    And I fill "Hours at maximum workers" with "4"
    And I fill "Minimum web servers" with "2"
    And I fill "Maximum web servers" with "5"
    And I fill "Hours at maximum web servers" with "4"
    And I fill "Number of schedulers" with "2"
    And I fill "Data storage size" with "50"
    And I click Save and add service
    Then the service "Amazon Managed Workflows for Apache Airflow" should be added successfully
    And a shareable estimate URL should be generated

    Examples: Environment size variants
      | env_size |
      | Small    |
      | Medium   |
      | Large    |
      | XL       |
      | 2XL      |

  # ============================================================
  # WINDOWS ON AWS
  # ============================================================

  @windows @windows-sql-ec2
  Scenario: Configure Windows Server and SQL Server on Amazon EC2 with all fields
    Given I search for "Windows Server and SQL Server on Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Machine description" with "Production SQL Server"
    And I fill "Storage amount (GB)" with "500"
    And I fill "IOPS" with "3000"
    And I fill "Number of vCPUs" with "8"
    And I fill "Memory (GiB)" with "32"
    And I fill "Quantity" with "2"
    And I click Save and add service
    Then the service "Windows Server and SQL Server on Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # HEALTH SERVICES
  # ============================================================

  @health @healthlake
  Scenario: Configure Amazon Healthlake with all fields
    Given I search for "Amazon Healthlake"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Additional Data Storage" with "100"
    And I fill "Total Number Of Queries per Month" with "50000"
    And I fill "Number Of NLP Characters" with "10000000"
    And I fill "Exported Data per GB" with "50"
    And I click Save and add service
    Then the service "Amazon Healthlake" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # DATA EXCHANGE & INTEGRATION
  # ============================================================

  @data @b2b-data-interchange
  Scenario: Configure AWS B2B Data Interchange with all fields
    Given I search for "AWS B2B Data Interchange"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of partnerships" with "5"
    And I fill "Number of transformation steps per month" with "10000"
    And I click Save and add service
    Then the service "AWS B2B Data Interchange" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # CLOUD MAP & DISCOVERY
  # ============================================================

  @discovery @cloud-map
  Scenario: Configure AWS Cloud Map with all fields
    Given I search for "AWS Cloud Map"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I click Save and add service
    Then the service "AWS Cloud Map" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # LOCATION SERVICES
  # ============================================================

  @location @location-service
  Scenario: Configure Amazon Location Service with all fields
    Given I search for "Amazon Location Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Dynamic Maps" with "100000"
    And I fill "Static Maps" with "10000"
    And I fill "Open Data Dynamic Maps" with "50000"
    And I click Save and add service
    Then the service "Amazon Location Service" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # ADDITIONAL VARIANT SCENARIOS - EXTENDED COVERAGE
  # ============================================================

  @compute @ec2 @spot
  Scenario: Configure Amazon EC2 - Spot instance
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "10"
    And I select "c6g.2xlarge" via autosuggest for "Search instance type"
    And I fill "Storage amount" with "50"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @compute @ec2 @gpu
  Scenario: Configure Amazon EC2 - GPU instance
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "1"
    And I select "p4d.24xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "1000"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @compute @ec2 @graviton
  Scenario: Configure Amazon EC2 - Graviton ARM instance
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "8"
    And I select "m7g.xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-postgresql @reserved
  Scenario: Configure Amazon RDS for PostgreSQL - Reserved pricing
    Given I search for "Amazon RDS for PostgreSQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I select "General Purpose SSD (gp3)" from dropdown "Storage type"
    And I fill "Nodes" with "3"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon RDS for PostgreSQL" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-mysql @reserved
  Scenario: Configure Amazon RDS for MySQL - Reserved pricing
    Given I search for "Amazon RDS for MySQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I select "General Purpose SSD (gp3)" from dropdown "Storage type"
    And I fill "Nodes" with "4"
    And I select "db.r6g.2xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "1000"
    And I click Save and add service
    Then the service "Amazon RDS for MySQL" should be added successfully
    And a shareable estimate URL should be generated

  @database @aurora-mysql @serverless
  Scenario: Configure Amazon Aurora MySQL-Compatible - Serverless workload
    Given I search for "Amazon Aurora MySQL-Compatible"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Aurora I/O-Optimized" from dropdown "Storage mode"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Nodes" with "1"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization" with "50"
    And I fill "Storage amount" with "500"
    And I fill "Baseline IO rate" with "5000"
    And I fill "Duration of peak IO activity" with "4"
    And I click Save and add service
    Then the service "Amazon Aurora MySQL-Compatible" should be added successfully
    And a shareable estimate URL should be generated

  @database @aurora-postgresql @extended-support
  Scenario: Configure Amazon Aurora PostgreSQL-Compatible DB - Extended Support
    Given I search for "Amazon Aurora PostgreSQL-Compatible DB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Aurora Standard" from dropdown "Storage mode"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Quantity" with "3"
    And I select "db.r6g.2xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization" with "100"
    And I fill "Storage amount" with "200"
    And I fill "Baseline IO rate" with "2000"
    And I fill "Number of hours running on Amazon RDS Extended Support" with "730"
    And I click Save and add service
    Then the service "Amazon Aurora PostgreSQL-Compatible DB" should be added successfully
    And a shareable estimate URL should be generated

  @database @dynamodb @global-tables
  Scenario: Configure Amazon DynamoDB - Global Tables workload
    Given I search for "Amazon DynamoDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Standard" from dropdown "Table class"
    And I fill "Average item size (all attributes)" with "500"
    And I fill "Percentage of Non-transactional writes Enter the percentage" with "80"
    And I fill "Baseline write rate" with "1000"
    And I fill "Peak write rate" with "10000"
    And I fill "Duration of peak write activity" with "6"
    And I fill "Baseline read rate" with "5000"
    And I fill "Peak read rate" with "50000"
    And I click Save and add service
    Then the service "Amazon DynamoDB" should be added successfully
    And a shareable estimate URL should be generated

  @database @elasticache @memcached-large
  Scenario: Configure Amazon ElastiCache - Large Memcached cluster
    Given I search for "Amazon ElastiCache"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Memcached" from dropdown "Engine"
    And I fill "Nodes" with "10"
    And I select "cache.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon ElastiCache" should be added successfully
    And a shareable estimate URL should be generated

  @database @neptune @large-graph
  Scenario: Configure Amazon Neptune - Large graph database
    Given I search for "Amazon Neptune"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Neptune I/O-Optimized" from dropdown "Storage mode"
    And I fill "Number of instances" with "4"
    And I select "db.r6g.2xlarge" via autosuggest for "Select an instance"
    And I fill "Usage (Neptune instances)" with "100"
    And I fill "Number of workbench instances" with "2"
    And I fill "Usage (Neptune Workbench instances)" with "50"
    And I fill "Data stored" with "200"
    And I fill "Number of I/O operations (Requests)" with "1000000"
    And I click Save and add service
    Then the service "Amazon Neptune" should be added successfully
    And a shareable estimate URL should be generated

  @database @documentdb @large-cluster
  Scenario: Configure Amazon DocumentDB - Large cluster
    Given I search for "Amazon DocumentDB (with MongoDB compatibility)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Amazon DocumentDB I/O-Optimized" from dropdown "Engine"
    And I fill "Quantity" with "6"
    And I select "db.r6g.2xlarge" via autosuggest for "Select an instance"
    And I fill "Server utilization" with "730"
    And I click Save and add service
    Then the service "Amazon DocumentDB (with MongoDB compatibility)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ebs @high-iops
  Scenario: Configure Amazon Elastic Block Store (EBS) - High IOPS workload
    Given I search for "Amazon Elastic Block Store (EBS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Provisioned IOPS SSD (io2)" from dropdown "Volume type"
    And I fill "Number of volumes" with "8"
    And I fill "Average duration of volume" with "730"
    And I fill "Storage amount per volume" with "1000"
    And I fill "Amount changed per snapshot" with "50"
    And I click Save and add service
    Then the service "Amazon Elastic Block Store (EBS)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @efs @large-storage
  Scenario: Configure Amazon Elastic File System (EFS) - Large storage with provisioned throughput
    Given I search for "Amazon Elastic File System (EFS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Provisioned Throughput" from dropdown "Throughput mode"
    And I fill "Desired Storage Capacity" with "5000"
    And I fill "Infrequent Access Tiering" with "40"
    And I fill "Infrequent Access Read" with "20"
    And I fill "Archive Access Tiering" with "10"
    And I fill "Archive Access Read" with "5"
    And I fill "Read Data Transferred" with "1000"
    And I fill "Write Data Transferred" with "500"
    And I click Save and add service
    Then the service "Amazon Elastic File System (EFS)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-lustre @high-throughput
  Scenario: Configure Amazon FSx for Lustre - High throughput SSD
    Given I search for "Amazon FSx for Lustre"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "SSD" from dropdown "Storage type"
    And I fill "Storage capacity" with "4800"
    And I fill "Metadata IOPS (optional)" with "3000"
    And I fill "Backup storage" with "2000"
    And I click Save and add service
    Then the service "Amazon FSx for Lustre" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-ontap @large
  Scenario: Configure Amazon FSx for NetApp ONTAP - Large Multi-AZ
    Given I search for "Amazon FSx for NetApp ONTAP"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ 2 Deployment" from dropdown "Deployment type"
    And I fill "Desired storage capacity" with "10240"
    And I fill "Desired additional SSD IOPS" with "10000"
    And I fill "Desired aggregate throughput" with "2048"
    And I fill "Read requests to capacity pool storage" with "1000000"
    And I fill "Write requests to capacity pool storage" with "500000"
    And I fill "Backup storage" with "5000"
    And I click Save and add service
    Then the service "Amazon FSx for NetApp ONTAP" should be added successfully
    And a shareable estimate URL should be generated

  @networking @cloudfront @enterprise
  Scenario: Configure Amazon CloudFront - Enterprise distribution
    Given I search for "Amazon CloudFront"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Pro Plan" with "2"
    And I fill "Business Plan" with "1"
    And I click Save and add service
    Then the service "Amazon CloudFront" should be added successfully
    And a shareable estimate URL should be generated

  @networking @network-firewall @multi-endpoint
  Scenario: Configure AWS Network Firewall - Multi-endpoint deployment
    Given I search for "AWS Network Firewall"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of AWS Network Firewall endpoints" with "6"
    And I fill "Monthly usage per endpoint" with "730"
    And I fill "Advanced Inspection Monthly usage per endpoint" with "730"
    And I fill "Number of Network Firewall secondary endpoints" with "6"
    And I fill "Usage per secondary endpoint" with "730"
    And I fill "Data processed per month" with "10000"
    And I click Save and add service
    Then the service "AWS Network Firewall" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @bedrock @nova-pro
  Scenario: Configure Amazon Bedrock - Nova Pro model
    Given I search for "Amazon Bedrock"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Geo Cross Region Inference" from dropdown "Inference type"
    And I select "On Demand - Standard" from dropdown "Pricing model"
    And I fill "Average requests per minute" with "50"
    And I fill "Hours per day at this rate" with "16"
    And I fill "Average input tokens per request" with "2000"
    And I fill "Average output tokens per request" with "1000"
    And I click Save and add service
    Then the service "Amazon Bedrock" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @bedrock @embeddings
  Scenario: Configure Amazon Bedrock - Embeddings workload
    Given I search for "Amazon Bedrock"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "In-Region" from dropdown "Inference type"
    And I select "On Demand - Standard" from dropdown "Pricing model"
    And I fill "Average requests per minute" with "200"
    And I fill "Hours per day at this rate" with "24"
    And I fill "Average input tokens per request" with "512"
    And I fill "Average output tokens per request" with "0"
    And I click Save and add service
    Then the service "Amazon Bedrock" should be added successfully
    And a shareable estimate URL should be generated

  @compute @fargate @batch
  Scenario: Configure AWS Fargate - Batch processing
    Given I search for "AWS Fargate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "ARM" from dropdown "CPU Architecture"
    And I fill "Number of tasks or pods" with "100"
    And I fill "Average duration" with "1800"
    And I fill "Amount of memory allocated" with "8"
    And I fill "Amount of ephemeral storage allocated for Amazon ECS" with "50"
    And I click Save and add service
    Then the service "AWS Fargate" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lambda @high-volume
  Scenario: Configure AWS Lambda - High volume event processing
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Arm" from dropdown "Architecture"
    And I fill "Number of requests" with "100000000"
    And I fill "Duration of each request (in ms)" with "50"
    And I fill "Amount of memory allocated" with "256"
    And I fill "Amount of ephemeral storage allocated" with "512"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

  @database @opensearch @large-cluster
  Scenario: Configure Amazon OpenSearch Service - Large cluster
    Given I search for "Amazon OpenSearch Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Nodes" with "9"
    And I select "r6g.xlarge.search" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Number of instances" with "3"
    And I fill "Storage amount per volume (gp3)" with "500"
    And I fill "Provisioning IOPS per volume (gp3)" with "5000"
    And I click Save and add service
    Then the service "Amazon OpenSearch Service" should be added successfully
    And a shareable estimate URL should be generated

  @integration @mq @rabbitmq
  Scenario: Configure Amazon MQ - RabbitMQ broker
    Given I search for "Amazon MQ"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Single-instance Broker" from dropdown "Broker type"
    And I select "mq.m5.2xlarge" from dropdown "Instance type"
    And I select "Durability optimized (Amazon EFS)" from dropdown "Storage type"
    And I fill "Number of Brokers running" with "3"
    And I fill "Storage per Broker" with "100"
    And I fill "Enter Amount" with "1000"
    And I click Save and add service
    Then the service "Amazon MQ" should be added successfully
    And a shareable estimate URL should be generated

  @workflow @managed-airflow @production
  Scenario: Configure Amazon Managed Workflows for Apache Airflow - Production setup
    Given I search for "Amazon Managed Workflows for Apache Airflow"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Large" from dropdown "Environment size"
    And I fill "Minimum workers" with "5"
    And I fill "Maximum workers" with "25"
    And I fill "Hours at maximum workers" with "8"
    And I fill "Minimum web servers" with "2"
    And I fill "Maximum web servers" with "5"
    And I fill "Hours at maximum web servers" with "8"
    And I fill "Number of schedulers" with "3"
    And I fill "Data storage size" with "200"
    And I click Save and add service
    Then the service "Amazon Managed Workflows for Apache Airflow" should be added successfully
    And a shareable estimate URL should be generated

  @security @kms @high-volume
  Scenario: Configure AWS Key Management Service - High volume encryption
    Given I search for "AWS Key Management Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of customer managed Customer Master Keys (CMK)" with "50"
    And I fill "Number of symmetric requests" with "50000000"
    And I fill "Number of asymmetric requests except RSA 2048" with "5000000"
    And I fill "Number of asymmetric requests involving RSA 2048" with "2000000"
    And I fill "Number of ECC GenerateDataKeyPair requests" with "1000000"
    And I fill "Number of RSA GenerateDataKeyPair requests" with "500000"
    And I click Save and add service
    Then the service "AWS Key Management Service" should be added successfully
    And a shareable estimate URL should be generated

  @management @cloudtrail @comprehensive
  Scenario: Configure AWS CloudTrail - Comprehensive logging
    Given I search for "AWS CloudTrail"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of management events" with "10000000"
    And I fill "Management event trails" with "3"
    And I fill "Read management events" with "5000000"
    And I fill "Read management trails" with "2"
    And I fill "S3 operations" with "50000000"
    And I fill "S3 trails" with "2"
    And I fill "Lambda data events" with "10000000"
    And I fill "Lambda trails" with "2"
    And I fill "Data ingested - CloudTrail" with "500"
    And I fill "Data scanned using queries" with "200"
    And I click Save and add service
    Then the service "AWS CloudTrail" should be added successfully
    And a shareable estimate URL should be generated

  @compute @amplify @large-site
  Scenario: Configure AWS Amplify - Large web application
    Given I search for "AWS Amplify"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of build minutes" with "5000"
    And I fill "Data stored per month" with "200"
    And I fill "Data served per month" with "2000"
    And I fill "Number of SSR requests" with "10000000"
    And I fill "Duration of each request (in ms)" with "200"
    And I click Save and add service
    Then the service "AWS Amplify" should be added successfully
    And a shareable estimate URL should be generated

  @integration @sns @high-volume
  Scenario: Configure Amazon Simple Notification Service (SNS) - High volume
    Given I search for "Amazon Simple Notification Service (SNS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Requests" with "100000000"
    And I fill "HTTP/HTTPS Notifications" with "50000000"
    And I fill "SQS Notifications" with "30000000"
    And I fill "Amazon Web Services Lambda" with "20000000"
    And I fill "Mobile Push Notifications" with "5000000"
    And I click Save and add service
    Then the service "Amazon Simple Notification Service (SNS)" should be added successfully
    And a shareable estimate URL should be generated

  @storage @backup @enterprise
  Scenario: Configure AWS Backup - Enterprise backup strategy
    Given I search for "AWS Backup"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Amount of primary data to be backed up" with "10000"
    And I fill "Estimated daily change of primary data" with "3"
    And I fill "Daily backups warm retention period" with "30"
    And I fill "Weekly backups warm retention period" with "52"
    And I fill "Monthly backups warm retention period" with "36"
    And I click Save and add service
    Then the service "AWS Backup" should be added successfully
    And a shareable estimate URL should be generated

  @media @medialive @large-broadcast
  Scenario: Configure AWS Elemental MediaLive - Large broadcast
    Given I search for "AWS Elemental MediaLive"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of inputs" with "8"
    And I fill "Active hours (On Demand)" with "730"
    And I fill "Number of outputs" with "16"
    And I click Save and add service
    Then the service "AWS Elemental MediaLive" should be added successfully
    And a shareable estimate URL should be generated

  @migration @dms @large-migration
  Scenario: Configure AWS Database Migration Service - Large migration
    Given I search for "AWS Database Migration Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of instances" with "5"
    And I select "dms.r5.2xlarge" via autosuggest for "Select an instance"
    And I fill "Storage amount (multiple AZ)" with "1000"
    And I click Save and add service
    Then the service "AWS Database Migration Service" should be added successfully
    And a shareable estimate URL should be generated

  @security @waf @comprehensive
  Scenario: Configure AWS Web Application Firewall (WAF) - Comprehensive rules
    Given I search for "AWS Web Application Firewall (WAF)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Web Access Control Lists (Web ACLs) utilized" with "10"
    And I fill "Number of Rules added per Web ACL" with "50"
    And I fill "Number of Rules inside each Rule Group" with "20"
    And I fill "Number of web requests received across all web ACLs" with "100000000"
    And I click Save and add service
    Then the service "AWS Web Application Firewall (WAF)" should be added successfully
    And a shareable estimate URL should be generated

  @security @cognito @enterprise
  Scenario: Configure Amazon Cognito - Enterprise user pool
    Given I search for "Amazon Cognito"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of monthly active users (MAU)" with "500000"
    And I fill "Number of monthly active users (MAU) who sign in through SAML or OIDC federation" with "100000"
    And I fill "Number of token requests" with "5000000"
    And I fill "Number of app clients" with "20"
    And I click Save and add service
    Then the service "Amazon Cognito" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @quicksight @enterprise
  Scenario: Configure Amazon QuickSight - Enterprise deployment
    Given I search for "Amazon QuickSight"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Readers" with "500"
    And I fill "Number of Authors" with "50"
    And I click Save and add service
    Then the service "Amazon QuickSight" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-mariadb @multi-az-gp3
  Scenario: Configure Amazon RDS for MariaDB - Multi-AZ gp3
    Given I search for "Amazon RDS for MariaDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I select "General Purpose SSD (gp3)" from dropdown "Storage type"
    And I fill "Nodes" with "3"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon RDS for MariaDB" should be added successfully
    And a shareable estimate URL should be generated

  @networking @data-transfer @large
  Scenario: Configure AWS Data Transfer - Large volume
    Given I search for "AWS Data Transfer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Enter Amount" with "100000"
    And I click Save and add service
    Then the service "AWS Data Transfer" should be added successfully
    And a shareable estimate URL should be generated

  @storage @datasync @large-migration
  Scenario: Configure AWS DataSync - Large data migration
    Given I search for "AWS DataSync"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total data copied by AWS DataSync per month" with "50000"
    And I click Save and add service
    Then the service "AWS DataSync" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-sitewise @enterprise
  Scenario: Configure AWS IoT SiteWise - Enterprise industrial
    Given I search for "AWS IoT SiteWise"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of daily measurements" with "50000000"
    And I fill "Number of tags or sensors" with "5000"
    And I fill "Cloud data availablity" with "90"
    And I fill "Buffer period" with "30"
    And I fill "Volume of data (GB)" with "500"
    And I fill "Count of monthly active users" with "50"
    And I click Save and add service
    Then the service "AWS IoT SiteWise" should be added successfully
    And a shareable estimate URL should be generated

  @compute @step-functions @express
  Scenario: Configure AWS Step Functions - Express workflows
    Given I search for "AWS Step Functions"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Workflow requests" with "10000000"
    And I fill "State transitions per workflow" with "5"
    And I click Save and add service
    Then the service "AWS Step Functions" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codebuild @large-builds
  Scenario: Configure AWS CodeBuild - Large build fleet
    Given I search for "AWS CodeBuild"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of builds in a month" with "5000"
    And I fill "Average build duration (minutes)" with "25"
    And I select "general1.large" via autosuggest for "Select an instance"
    And I click Save and add service
    Then the service "AWS CodeBuild" should be added successfully
    And a shareable estimate URL should be generated

  @management @config @enterprise
  Scenario: Configure AWS Config - Enterprise compliance
    Given I search for "AWS Config"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Continuous Configuration items recorded" with "50000"
    And I fill "Number of Periodic Configuration items recorded" with "10000"
    And I fill "Number of Config rule evaluations" with "100000"
    And I fill "Number of Conformance pack evaluations" with "50000"
    And I click Save and add service
    Then the service "AWS Config" should be added successfully
    And a shareable estimate URL should be generated

  @security @secrets-manager @large
  Scenario: Configure AWS Secrets Manager - Large deployment
    Given I search for "AWS Secrets Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of secrets" with "5000"
    And I fill "Average duration of each secret" with "30"
    And I fill "Number of API calls" with "50000000"
    And I click Save and add service
    Then the service "AWS Secrets Manager" should be added successfully
    And a shareable estimate URL should be generated

  @database @redshift @serverless
  Scenario: Configure Amazon Redshift - Large cluster with RA3
    Given I search for "Amazon Redshift"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Nodes" with "8"
    And I select "ra3.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon Redshift" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lightsail @container
  Scenario: Configure Amazon Lightsail - Container focused
    Given I search for "Amazon Lightsail"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of servers" with "1"
    And I select "large" via autosuggest for "Select an instance"
    And I fill "Server utilization" with "100"
    And I fill "Number of containers" with "10"
    And I fill "Container utilization" with "95"
    And I click Save and add service
    Then the service "Amazon Lightsail" should be added successfully
    And a shareable estimate URL should be generated

  @business @workspaces @large-deployment
  Scenario: Configure Amazon WorkSpaces - Large enterprise deployment
    Given I search for "Amazon WorkSpaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Windows" from dropdown "Operating system"
    And I fill "Number of WorkSpaces" with "500"
    And I fill "Billing option" with "730"
    And I click Save and add service
    Then the service "Amazon WorkSpaces" should be added successfully
    And a shareable estimate URL should be generated

  @storage @s3 @data-lake
  Scenario: Configure Amazon Simple Storage Service (S3) - Data lake workload
    Given I search for "Amazon Simple Storage Service (S3)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "S3 Standard storage" with "100000"
    And I fill "PUT, COPY, POST, LIST requests to S3 Standard" with "50000000"
    And I fill "GET, SELECT, and all other requests from S3 Standard" with "200000000"
    And I fill "Data returned by S3 Select" with "5000"
    And I fill "Enter Amount" with "50000"
    And I click Save and add service
    Then the service "Amazon Simple Storage Service (S3)" should be added successfully
    And a shareable estimate URL should be generated

  @networking @elb @nlb
  Scenario: Configure Elastic Load Balancing - Network Load Balancer focus
    Given I search for "Elastic Load Balancing"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Application Load Balancers" with "5"
    And I fill "Processed bytes (Lambda functions as targets)" with "500"
    And I fill "Average number of new connections per ALB" with "500"
    And I fill "Average number of requests per second per ALB" with "2000"
    And I fill "Average number of rule evaluations per request" with "15"
    And I click Save and add service
    Then the service "Elastic Load Balancing" should be added successfully
    And a shareable estimate URL should be generated

  @management @systems-manager @fleet
  Scenario: Configure AWS Systems Manager - Fleet management
    Given I search for "AWS Systems Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Standard parameters" with "1000"
    And I fill "Advanced parameters" with "100"
    And I fill "Frequency of API interactions per parameter" with "10000"
    And I click Save and add service
    Then the service "AWS Systems Manager" should be added successfully
    And a shareable estimate URL should be generated

  @security @security-hub @multi-account
  Scenario: Configure AWS Security Hub - Multi-account organization
    Given I search for "AWS Security Hub"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Accounts" with "50"
    And I fill "Number of Security Checks per Account" with "1000"
    And I fill "Number of Finding Ingested per Account" with "50000"
    And I fill "Number of Automation Rules" with "50"
    And I fill "Number of criteria in each automation rule" with "5"
    And I click Save and add service
    Then the service "AWS Security Hub" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-greengrass @large-fleet
  Scenario: Configure AWS IoT Greengrass - Large edge fleet
    Given I search for "AWS IoT Greengrass"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of greengrass core devices" with "500"
    And I fill "Activity Period in minutes per month" with "43200"
    And I fill "MQTT topics with cloud as source (optional)" with "50"
    And I fill "Number of client devices per greengrass core device (optional)" with "10"
    And I click Save and add service
    Then the service "AWS IoT Greengrass" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediapackage @live-vod
  Scenario: Configure AWS Elemental MediaPackage - Live and VOD
    Given I search for "AWS Elemental MediaPackage"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of inputs per channel" with "4"
    And I fill "Total duration of live streams per month" with "730"
    And I fill "Ingest bitrate per input (Mbit per second)" with "10"
    And I fill "Average Number of viewers per hour" with "10000"
    And I fill "Average bitrate per viewer (Mbit per second)" with "5"
    And I fill "Hours of VOD content watched" with "50000"
    And I click Save and add service
    Then the service "AWS Elemental MediaPackage" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @lake-formation @large
  Scenario: Configure AWS Lake Formation - Enterprise data lake
    Given I search for "AWS Lake Formation"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data scanned" with "1000"
    And I fill "Storage usage in a month (in millions)" with "50"
    And I fill "Requests in a month (in millions)" with "100"
    And I fill "Number of tables" with "500"
    And I fill "Number of small files ingested per table per day" with "100"
    And I fill "Size of small files (less than 64MB)" with "10"
    And I click Save and add service
    Then the service "AWS Lake Formation" should be added successfully
    And a shareable estimate URL should be generated

  @integration @appsync @high-traffic
  Scenario: Configure AWS AppSync - High traffic GraphQL
    Given I search for "AWS AppSync"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of API Requests" with "100000000"
    And I fill "Enter Amount" with "5000"
    And I click Save and add service
    Then the service "AWS AppSync" should be added successfully
    And a shareable estimate URL should be generated

  @compute @eks @multi-cluster
  Scenario: Configure Amazon EKS - Multi-cluster deployment
    Given I search for "Amazon EKS"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of EKS Clusters" with "10"
    And I click Save and add service
    Then the service "Amazon EKS" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codepipeline @large
  Scenario: Configure AWS CodePipeline - Large CI/CD platform
    Given I search for "AWS CodePipeline"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of active pipelines of type V1 used per account per month" with "25"
    And I fill "Number of action execution minutes used in pipeline of type V2 per account per month" with "10000"
    And I click Save and add service
    Then the service "AWS CodePipeline" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @ses @high-volume
  Scenario: Configure Amazon Simple Email Service (SES) - High volume sending
    Given I search for "Amazon Simple Email Service (SES)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Open Ingress Endpoint(s)" with "3"
    And I fill "Number of Emails processed by Mail Manager" with "5000000"
    And I fill "Email messages sent from EC2" with "2000000"
    And I fill "Attachment data sent from EC2" with "5000"
    And I fill "Email messages sent from email client" with "500000"
    And I fill "Email messages received" with "1000000"
    And I click Save and add service
    Then the service "Amazon Simple Email Service (SES)" should be added successfully
    And a shareable estimate URL should be generated

  @security @firewall-manager @enterprise
  Scenario: Configure AWS Firewall Manager - Enterprise security
    Given I search for "AWS Firewall Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of protection policy" with "20"
    And I fill "Number of aws account" with "50"
    And I fill "Number of Configuration items recorded" with "10000"
    And I fill "Number of Config rule evaluations" with "50000"
    And I fill "Number of AWS Network Firewall endpoints" with "10"
    And I fill "Data processed per month" with "5000"
    And I click Save and add service
    Then the service "AWS Firewall Manager" should be added successfully
    And a shareable estimate URL should be generated

  @health @healthlake @large
  Scenario: Configure Amazon Healthlake - Large healthcare dataset
    Given I search for "Amazon Healthlake"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Additional Data Storage" with "1000"
    And I fill "Total Number Of Queries per Month" with "500000"
    And I fill "Number Of NLP Characters" with "100000000"
    And I fill "Exported Data per GB" with "500"
    And I fill "Number of notifications to Amazon EventBridge" with "100000"
    And I click Save and add service
    Then the service "Amazon Healthlake" should be added successfully
    And a shareable estimate URL should be generated

  @windows @windows-sql-ec2 @ha-cluster
  Scenario: Configure Windows Server and SQL Server on Amazon EC2 - HA cluster
    Given I search for "Windows Server and SQL Server on Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Machine description" with "SQL Server HA Cluster"
    And I fill "Storage amount (GB)" with "2000"
    And I fill "IOPS" with "10000"
    And I fill "Throughput (MiB/s)" with "500"
    And I fill "Number of vCPUs" with "32"
    And I fill "Memory (GiB)" with "128"
    And I fill "Quantity" with "4"
    And I fill "Number of passive instances" with "2"
    And I click Save and add service
    Then the service "Windows Server and SQL Server on Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @compute @gamelift-servers @large-game
  Scenario: Configure Amazon GameLift Servers - Large multiplayer game
    Given I search for "Amazon GameLift Servers"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Peak concurrent players (peak CCU)" with "50000"
    And I fill "Game sessions per instance" with "8"
    And I fill "Players per game session" with "100"
    And I select "c5.2xlarge" via autosuggest for "Select an instance"
    And I click Save and add service
    Then the service "Amazon GameLift Servers" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @rekognition @video-analysis
  Scenario: Configure Amazon Rekognition - High volume image processing
    Given I search for "Amazon Rekognition"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of images processed with labels API calls per month" with "5000000"
    And I fill "Number of images processed with content moderation API calls per month" with "2000000"
    And I fill "Number of images processed with detect text API calls per month" with "1000000"
    And I fill "Number of images processed with celebrity API calls per month" with "500000"
    And I fill "Number of images processed with PPE detection API calls per month" with "300000"
    And I fill "Number of DetectFaces API calls per month" with "1000000"
    And I click Save and add service
    Then the service "Amazon Rekognition" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @managed-flink @production
  Scenario: Configure Amazon Managed Service for Apache Flink - Production
    Given I search for "Amazon Managed Service for Apache Flink"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Apache Flink applications" with "5"
    And I fill "Apache Flink KPUs" with "16"
    And I fill "Durable application backups maintained" with "10"
    And I fill "Durable application backup storage (average size)" with "50"
    And I fill "Studio applications" with "3"
    And I click Save and add service
    Then the service "Amazon Managed Service for Apache Flink" should be added successfully
    And a shareable estimate URL should be generated

  @security @macie @large-scan
  Scenario: Configure Amazon Macie - Large S3 scanning
    Given I search for "Amazon Macie"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of S3 buckets" with "500"
    And I fill "Total bytes in S3 storage" with "100000"
    And I fill "Number of objects monitored for automated data discovery" with "500000000"
    And I click Save and add service
    Then the service "Amazon Macie" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # SCALE TESTING SCENARIOS - PRODUCTION WORKLOADS
  # ============================================================

  @compute @ec2 @windows-sql
  Scenario: Configure Amazon EC2 - Windows with SQL Server
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Windows Server with SQL Server Standard" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "4"
    And I select "r6i.2xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @compute @ec2 @linux-sql
  Scenario: Configure Amazon EC2 - Linux with SQL Server
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux with SQL Server Standard" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "2"
    And I select "r6i.xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "300"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @compute @ec2 @dedicated-host
  Scenario: Configure Amazon EC2 - Dedicated Hosts
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Linux" from dropdown "Operating system"
    And I select "Dedicated Hosts" from dropdown "Tenancy"
    And I fill "Number of instances" with "1"
    And I select "m6i.metal" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "2000"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-postgresql @single-io2
  Scenario: Configure Amazon RDS for PostgreSQL - Single-AZ io2 high performance
    Given I search for "Amazon RDS for PostgreSQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Single-AZ" from dropdown "Deployment Option"
    And I select "Provisioned IOPS SSD (io2)" from dropdown "Storage type"
    And I fill "Nodes" with "1"
    And I select "db.r6g.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "2000"
    And I click Save and add service
    Then the service "Amazon RDS for PostgreSQL" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-mysql @multi-az-io2
  Scenario: Configure Amazon RDS for MySQL - Multi-AZ io2 high performance
    Given I search for "Amazon RDS for MySQL"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I select "Provisioned IOPS SSD (io2)" from dropdown "Storage type"
    And I fill "Nodes" with "1"
    And I select "db.r6g.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "2000"
    And I click Save and add service
    Then the service "Amazon RDS for MySQL" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ebs @throughput-hdd
  Scenario: Configure Amazon Elastic Block Store (EBS) - Throughput HDD with snapshots
    Given I search for "Amazon Elastic Block Store (EBS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Throughput Optimized HDD (st 1)" from dropdown "Volume type"
    And I fill "Number of volumes" with "10"
    And I fill "Average duration of volume" with "730"
    And I fill "Storage amount per volume" with "2000"
    And I fill "Amount changed per snapshot" with "100"
    And I fill "Number of snapshots to restore" with "5"
    And I click Save and add service
    Then the service "Amazon Elastic Block Store (EBS)" should be added successfully
    And a shareable estimate URL should be generated

  @database @elasticache @valkey-reserved
  Scenario: Configure Amazon ElastiCache - Valkey Reserved large
    Given I search for "Amazon ElastiCache"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Valkey" from dropdown "Engine"
    And I select "Reserved" from dropdown "Pricing model"
    And I fill "Nodes" with "6"
    And I select "cache.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon ElastiCache" should be added successfully
    And a shareable estimate URL should be generated

  @database @aurora-mysql @high-io
  Scenario: Configure Amazon Aurora MySQL-Compatible - High IO workload
    Given I search for "Amazon Aurora MySQL-Compatible"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Aurora I/O-Optimized" from dropdown "Storage mode"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Nodes" with "4"
    And I select "db.r6g.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization" with "100"
    And I fill "Storage amount" with "1000"
    And I fill "Baseline IO rate" with "50000"
    And I fill "Duration of peak IO activity" with "8"
    And I click Save and add service
    Then the service "Amazon Aurora MySQL-Compatible" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-windows @multi-az
  Scenario: Configure Amazon FSx for Windows File Server - Multi-AZ HA
    Given I search for "Amazon FSx for Windows File Server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Desired storage capacity" with "5120"
    And I fill "Desired aggregate throughput" with "1024"
    And I fill "Backup storage" with "2000"
    And I click Save and add service
    Then the service "Amazon FSx for Windows File Server" should be added successfully
    And a shareable estimate URL should be generated

  @networking @waf @bot-control
  Scenario: Configure AWS Web Application Firewall (WAF) - Bot Control
    Given I search for "AWS Web Application Firewall (WAF)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Web Access Control Lists (Web ACLs) utilized" with "5"
    And I fill "Number of Rules added per Web ACL" with "25"
    And I fill "Number of Rules inside each Rule Group" with "10"
    And I fill "Number of web requests received across all web ACLs" with "500000000"
    And I click Save and add service
    Then the service "AWS Web Application Firewall (WAF)" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @bedrock @high-volume-batch
  Scenario: Configure Amazon Bedrock - High volume batch processing
    Given I search for "Amazon Bedrock"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Geo Cross Region Inference" from dropdown "Inference type"
    And I select "Batch" from dropdown "Pricing model"
    And I fill "Average requests per minute" with "100"
    And I fill "Hours per day at this rate" with "24"
    And I fill "Average input tokens per request" with "5000"
    And I fill "Average output tokens per request" with "2000"
    And I click Save and add service
    Then the service "Amazon Bedrock" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @sagemaker @training
  Scenario: Configure Amazon SageMaker - Training focused
    Given I search for "Amazon SageMaker"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of data scientist(s)" with "5"
    And I fill "Number of Studio Notebook instances per data scientist" with "2"
    And I fill "Studio Notebook hour(s) per day" with "12"
    And I fill "Studio Notebook day(s) per month" with "30"
    And I fill "Number of On-Demand Notebook instances per data scientist" with "1"
    And I fill "On-Demand Notebook hour(s) per day" with "8"
    And I fill "On-Demand Notebook day(s) per month" with "22"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon SageMaker" should be added successfully
    And a shareable estimate URL should be generated

  @compute @fargate @windows-large
  Scenario: Configure AWS Fargate - Windows containers large deployment
    Given I search for "AWS Fargate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Windows" from dropdown "Operating system"
    And I select "x86" from dropdown "CPU Architecture"
    And I fill "Number of tasks or pods" with "25"
    And I fill "Average duration" with "3600"
    And I fill "Amount of memory allocated" with "8"
    And I fill "Amount of ephemeral storage allocated for Amazon ECS" with "50"
    And I click Save and add service
    Then the service "AWS Fargate" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lambda @edge
  Scenario: Configure AWS Lambda - Edge functions
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "x86" from dropdown "Architecture"
    And I fill "Number of requests" with "500000000"
    And I fill "Duration of each request (in ms)" with "5"
    And I fill "Amount of memory allocated" with "128"
    And I fill "Amount of ephemeral storage allocated" with "512"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @kinesis-data-streams @real-time
  Scenario: Configure Amazon Kinesis Data Streams - Real-time analytics
    Given I search for "Amazon Kinesis Data Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of records" with "10000000"
    And I fill "Average record size" with "1"
    And I fill "Number of Consumer Applications" with "3"
    And I fill "Number of days for data retention" with "3"
    And I fill "Number of Enhanced fan-out consumers" with "5"
    And I click Save and add service
    Then the service "Amazon Kinesis Data Streams" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @msk @serverless
  Scenario: Configure Amazon Managed Streaming for Apache Kafka (MSK) - Enterprise streaming
    Given I search for "Amazon Managed Streaming for Apache Kafka (MSK)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Kafka broker nodes" with "6"
    And I select "kafka.m5.4xlarge" via autosuggest for "Select an instance"
    And I fill "Storage per Broker" with "5000"
    And I fill "Desired Provisioned Storage Throughput (MiBps)" with "1000"
    And I fill "Enter Amount" with "10000"
    And I click Save and add service
    Then the service "Amazon Managed Streaming for Apache Kafka (MSK)" should be added successfully
    And a shareable estimate URL should be generated

  @integration @mq @ha-large
  Scenario: Configure Amazon MQ - High availability large deployment
    Given I search for "Amazon MQ"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Active/standby-instance Broker" from dropdown "Broker type"
    And I select "mq.m5.4xlarge" from dropdown "Instance type"
    And I select "Durability optimized (Amazon EFS)" from dropdown "Storage type"
    And I fill "Number of Brokers running" with "5"
    And I fill "Storage per Broker" with "200"
    And I fill "Enter Amount" with "5000"
    And I click Save and add service
    Then the service "Amazon MQ" should be added successfully
    And a shareable estimate URL should be generated

  @database @opensearch @reserved-large
  Scenario: Configure Amazon OpenSearch Service - Reserved large cluster
    Given I search for "Amazon OpenSearch Service"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Reserved" from dropdown "Pricing model"
    And I fill "Nodes" with "12"
    And I select "r6g.2xlarge.search" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Number of instances" with "3"
    And I fill "Storage amount per volume (gp3)" with "1000"
    And I fill "Provisioning IOPS per volume (gp3)" with "10000"
    And I fill "Number of nodes" with "3"
    And I click Save and add service
    Then the service "Amazon OpenSearch Service" should be added successfully
    And a shareable estimate URL should be generated

  @workflow @managed-airflow @2xl
  Scenario: Configure Amazon Managed Workflows for Apache Airflow - 2XL production
    Given I search for "Amazon Managed Workflows for Apache Airflow"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "2XL" from dropdown "Environment size"
    And I fill "Minimum workers" with "10"
    And I fill "Maximum workers" with "50"
    And I fill "Hours at maximum workers" with "12"
    And I fill "Minimum web servers" with "3"
    And I fill "Maximum web servers" with "10"
    And I fill "Hours at maximum web servers" with "8"
    And I fill "Number of schedulers" with "3"
    And I fill "Data storage size" with "500"
    And I click Save and add service
    Then the service "Amazon Managed Workflows for Apache Airflow" should be added successfully
    And a shareable estimate URL should be generated

  @business @workspaces @ubuntu
  Scenario: Configure Amazon WorkSpaces - Ubuntu development
    Given I search for "Amazon WorkSpaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Ubuntu Linux" from dropdown "Operating system"
    And I fill "Number of WorkSpaces" with "50"
    And I fill "Billing option" with "730"
    And I click Save and add service
    Then the service "Amazon WorkSpaces" should be added successfully
    And a shareable estimate URL should be generated

  @management @xray @high-traffic
  Scenario: Configure AWS X-Ray - High traffic application
    Given I search for "AWS X-Ray"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of requests per month" with "100000000"
    And I fill "Number of queries per month" with "100000"
    And I fill "Traces retrieved per query" with "500"
    And I click Save and add service
    Then the service "AWS X-Ray" should be added successfully
    And a shareable estimate URL should be generated

  @networking @shield @comprehensive
  Scenario: Configure AWS Shield - Comprehensive protection
    Given I search for "AWS Shield"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Cloud Front Usage" with "50"
    And I fill "Elastic Load Balancing (ELB) Usage" with "20"
    And I fill "Elastic IP Usage" with "15"
    And I fill "Global Accelerator Usage" with "5"
    And I click Save and add service
    Then the service "AWS Shield" should be added successfully
    And a shareable estimate URL should be generated

  @security @iam-access-analyzer @organization
  Scenario: Configure AWS IAM Access Analyzer - Organization wide
    Given I search for "AWS IAM Access Analyzer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of accounts to monitor" with "50"
    And I fill "Average roles per account" with "200"
    And I fill "Average users per account" with "500"
    And I fill "Number of analyzers per account" with "3"
    And I fill "Number of requests to CheckNoNewAccess API" with "100000"
    And I fill "Number of requests to CheckAccessNotGranted API" with "50000"
    And I fill "Number of resources to monitor" with "10000"
    And I click Save and add service
    Then the service "AWS IAM Access Analyzer" should be added successfully
    And a shareable estimate URL should be generated

  @migration @transfer-family @enterprise
  Scenario: Configure AWS Transfer Family - Enterprise file transfer
    Given I search for "AWS Transfer Family"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of endpoints with AS2 enabled" with "5"
    And I fill "Number of AS2 messages sent per month" with "100000"
    And I fill "Number of AS2 messages received per month" with "100000"
    And I click Save and add service
    Then the service "AWS Transfer Family" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-analytics @large
  Scenario: Configure AWS IoT Analytics - Large scale analytics
    Given I search for "AWS IoT Analytics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of IoT devices (monthly)" with "50000"
    And I fill "Data generation by each device" with "100"
    And I fill "Number of data pipelines (monthly)" with "20"
    And I fill "Data queried per month" with "5000"
    And I fill "Number of queries (monthly)" with "10000"
    And I fill "Data scanned per query" with "10"
    And I click Save and add service
    Then the service "AWS IoT Analytics" should be added successfully
    And a shareable estimate URL should be generated

  @compute @emr @gpu-cluster
  Scenario: Configure Amazon EMR - GPU accelerated cluster
    Given I search for "Amazon EMR"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of master EMR nodes" with "1"
    And I fill "Utilization" with "100"
    And I fill "Number of core EMR nodes" with "8"
    And I click Save and add service
    Then the service "Amazon EMR" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-oracle @multi-az
  Scenario: Configure Amazon RDS for Oracle - Multi-AZ high availability
    Given I search for "Amazon RDS for Oracle"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I fill "Nodes" with "2"
    And I select "db.r6i.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "1000"
    And I click Save and add service
    Then the service "Amazon RDS for Oracle" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-sql-server @enterprise
  Scenario: Configure Amazon RDS for SQL server - Enterprise Multi-AZ
    Given I search for "Amazon RDS for SQL server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I fill "Nodes" with "2"
    And I select "db.r6i.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "1000"
    And I click Save and add service
    Then the service "Amazon RDS for SQL server" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-db2 @production
  Scenario: Configure Amazon RDS for Db2 - Production Multi-AZ
    Given I search for "Amazon RDS for Db2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I fill "Nodes" with "2"
    And I select "db.r6i.2xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon RDS for Db2" should be added successfully
    And a shareable estimate URL should be generated

  @integration @eventbridge @scheduler
  Scenario: Configure Amazon EventBridge - Scheduler and Pipes
    Given I search for "Amazon EventBridge"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of the payload" with "256"
    And I fill "Number of custom events" with "50000000"
    And I fill "Number of events" with "10000000"
    And I fill "Number of invocations" with "5000000"
    And I fill "Number of requests" with "1000000"
    And I click Save and add service
    Then the service "Amazon EventBridge" should be added successfully
    And a shareable estimate URL should be generated

  @security @private-ca @enterprise
  Scenario: Configure AWS Private Certificate Authority - Enterprise PKI
    Given I search for "AWS Private Certificate Authority"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Private CAs" with "5"
    And I fill "Number of general purpose mode private certificates issued" with "10000"
    And I fill "Number of certificates used with ACM-integrated services" with "5000"
    And I fill "Number of short lived certificate mode private certificates issued" with "100000"
    And I fill "Number of OCSP responses per Month" with "5000000"
    And I click Save and add service
    Then the service "AWS Private Certificate Authority" should be added successfully
    And a shareable estimate URL should be generated

  @management @managed-prometheus @large
  Scenario: Configure Amazon Managed Service for Prometheus - Large deployment
    Given I search for "Amazon Managed Service for Prometheus"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average active time series" with "5000000"
    And I fill "Avg Collection Interval (in seconds)" with "15"
    And I fill "Retention Period (in days)" with "365"
    And I fill "Average Number of Dashboard users per day" with "20"
    And I fill "Number of Prometheus rules" with "500"
    And I fill "Average rule execution interval (in seconds)" with "60"
    And I fill "Number of collectors" with "10"
    And I click Save and add service
    Then the service "Amazon Managed Service for Prometheus" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @data-firehose @vended-logs
  Scenario: Configure Amazon Data firehose - Vended logs
    Given I search for "Amazon Data firehose"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Vended logs" from dropdown "Source"
    And I fill "Number of records for data ingestion" with "10000"
    And I fill "Record size" with "2"
    And I click Save and add service
    Then the service "Amazon Data firehose" should be added successfully
    And a shareable estimate URL should be generated

  @security @detective @enterprise
  Scenario: Configure Amazon Detective - Enterprise investigation
    Given I search for "Amazon Detective"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data ingested from AWS CloudTrail, Amazon VPC Flow Logs, Amazon GuardDuty (per account, per region)" with "1000"
    And I click Save and add service
    Then the service "Amazon Detective" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codeartifact @enterprise
  Scenario: Configure AWS CodeArtifact - Enterprise artifact management
    Given I search for "AWS CodeArtifact"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of artifacts stored" with "500"
    And I fill "Number of API requests" with "5000000"
    And I fill "Enter Amount" with "2000"
    And I click Save and add service
    Then the service "AWS CodeArtifact" should be added successfully
    And a shareable estimate URL should be generated

  @management @managed-grafana @enterprise
  Scenario: Configure Amazon Managed Grafana - Enterprise monitoring
    Given I search for "Amazon Managed Grafana"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of active editors/administrators" with "20"
    And I fill "Number of active viewers" with "200"
    And I click Save and add service
    Then the service "Amazon Managed Grafana" should be added successfully
    And a shareable estimate URL should be generated

  @security @cloudhsm @cluster
  Scenario: Configure AWS CloudHSM - HA cluster
    Given I search for "AWS CloudHSM"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of hsm1.medium HSMs" with "6"
    And I fill "Total number of hsm2m.medium HSMs" with "3"
    And I click Save and add service
    Then the service "AWS CloudHSM" should be added successfully
    And a shareable estimate URL should be generated

  @compute @deadline-cloud @render-farm
  Scenario: Configure AWS Deadline Cloud - Render farm
    Given I search for "AWS Deadline Cloud"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Instance" with "50"
    And I select "c5.4xlarge" via autosuggest for "Select an instance"
    And I fill "Monthly utilization" with "400"
    And I fill "Storage per worker" with "500"
    And I fill "Utilization (On-Demand only)" with "60"
    And I click Save and add service
    Then the service "AWS Deadline Cloud" should be added successfully
    And a shareable estimate URL should be generated

  @networking @direct-connect @multi-port
  Scenario: Configure AWS Direct Connect - Multi-port high capacity
    Given I search for "AWS Direct Connect"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of ports" with "8"
    And I fill "Hours used" with "730"
    And I fill "Data transfer out" with "200000"
    And I fill "Data transfer in (free)" with "500000"
    And I click Save and add service
    Then the service "AWS Direct Connect" should be added successfully
    And a shareable estimate URL should be generated

  @integration @swf @high-volume
  Scenario: Configure Amazon Simple Workflow Service (SWF) - High volume
    Given I search for "Amazon Simple Workflow Service (SWF)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Workflow Executions" with "100000"
    And I fill "Total Tasks, Markers, Timers and Signals" with "500000"
    And I fill "Workflow lifetime" with "7"
    And I fill "Workflow retention" with "30"
    And I click Save and add service
    Then the service "Amazon Simple Workflow Service (SWF)" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # REGIONAL DEPLOYMENT SCENARIOS
  # ============================================================

  @compute @ec2 @eu-region
  Scenario: Configure Amazon EC2 - EU West deployment
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I select "Linux" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "5"
    And I select "m6i.xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-postgresql @eu-region
  Scenario: Configure Amazon RDS for PostgreSQL - EU West deployment
    Given I search for "Amazon RDS for PostgreSQL"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I select "Multi-AZ" from dropdown "Deployment Option"
    And I select "General Purpose SSD (gp3)" from dropdown "Storage type"
    And I fill "Nodes" with "2"
    And I select "db.m6i.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "200"
    And I click Save and add service
    Then the service "Amazon RDS for PostgreSQL" should be added successfully
    And a shareable estimate URL should be generated

  @compute @fargate @ap-region
  Scenario: Configure AWS Fargate - Asia Pacific deployment
    Given I search for "AWS Fargate"
    And I click Configure
    When I set the region to "Asia Pacific (Tokyo)"
    And I select "Linux" from dropdown "Operating system"
    And I select "x86" from dropdown "CPU Architecture"
    And I fill "Number of tasks or pods" with "20"
    And I fill "Average duration" with "600"
    And I fill "Amount of memory allocated" with "4"
    And I fill "Amount of ephemeral storage allocated for Amazon ECS" with "30"
    And I click Save and add service
    Then the service "AWS Fargate" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lambda @ap-region
  Scenario: Configure AWS Lambda - Asia Pacific deployment
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "Asia Pacific (Singapore)"
    And I select "Arm" from dropdown "Architecture"
    And I fill "Number of requests" with "50000000"
    And I fill "Duration of each request (in ms)" with "150"
    And I fill "Amount of memory allocated" with "512"
    And I fill "Amount of ephemeral storage allocated" with "512"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

  @storage @s3 @eu-region
  Scenario: Configure Amazon Simple Storage Service (S3) - EU deployment
    Given I search for "Amazon Simple Storage Service (S3)"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I fill "S3 Standard storage" with "5000"
    And I fill "PUT, COPY, POST, LIST requests to S3 Standard" with "1000000"
    And I fill "GET, SELECT, and all other requests from S3 Standard" with "5000000"
    And I fill "Data returned by S3 Select" with "200"
    And I click Save and add service
    Then the service "Amazon Simple Storage Service (S3)" should be added successfully
    And a shareable estimate URL should be generated

  @database @aurora-postgresql @ap-region
  Scenario: Configure Amazon Aurora PostgreSQL-Compatible DB - AP deployment
    Given I search for "Amazon Aurora PostgreSQL-Compatible DB"
    And I click Configure
    When I set the region to "Asia Pacific (Sydney)"
    And I select "Aurora Standard" from dropdown "Storage mode"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Quantity" with "3"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization" with "100"
    And I fill "Storage amount" with "200"
    And I fill "Baseline IO rate" with "5000"
    And I click Save and add service
    Then the service "Amazon Aurora PostgreSQL-Compatible DB" should be added successfully
    And a shareable estimate URL should be generated

  @networking @elb @eu-region
  Scenario: Configure Elastic Load Balancing - EU deployment
    Given I search for "Elastic Load Balancing"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I fill "Number of Application Load Balancers" with "4"
    And I fill "Processed bytes (Lambda functions as targets)" with "200"
    And I fill "Average number of new connections per ALB" with "200"
    And I fill "Average number of requests per second per ALB" with "1000"
    And I fill "Average number of rule evaluations per request" with "10"
    And I click Save and add service
    Then the service "Elastic Load Balancing" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @bedrock @eu-region
  Scenario: Configure Amazon Bedrock - EU deployment
    Given I search for "Amazon Bedrock"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I select "In-Region" from dropdown "Inference type"
    And I select "On Demand - Standard" from dropdown "Pricing model"
    And I fill "Average requests per minute" with "20"
    And I fill "Hours per day at this rate" with "12"
    And I fill "Average input tokens per request" with "1000"
    And I fill "Average output tokens per request" with "500"
    And I click Save and add service
    Then the service "Amazon Bedrock" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ebs @eu-region
  Scenario: Configure Amazon Elastic Block Store (EBS) - EU gp3
    Given I search for "Amazon Elastic Block Store (EBS)"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I select "General Purpose SSD (gp3)" from dropdown "Volume type"
    And I fill "Number of volumes" with "20"
    And I fill "Average duration of volume" with "730"
    And I fill "Storage amount per volume" with "200"
    And I fill "Amount changed per snapshot" with "20"
    And I click Save and add service
    Then the service "Amazon Elastic Block Store (EBS)" should be added successfully
    And a shareable estimate URL should be generated

  @database @dynamodb @ap-region
  Scenario: Configure Amazon DynamoDB - Asia Pacific deployment
    Given I search for "Amazon DynamoDB"
    And I click Configure
    When I set the region to "Asia Pacific (Tokyo)"
    And I select "Standard" from dropdown "Table class"
    And I fill "Average item size (all attributes)" with "100"
    And I fill "Baseline write rate" with "500"
    And I fill "Peak write rate" with "2000"
    And I fill "Duration of peak write activity" with "4"
    And I fill "Baseline read rate" with "2000"
    And I fill "Peak read rate" with "10000"
    And I click Save and add service
    Then the service "Amazon DynamoDB" should be added successfully
    And a shareable estimate URL should be generated

  @database @elasticache @eu-region
  Scenario: Configure Amazon ElastiCache - EU Redis deployment
    Given I search for "Amazon ElastiCache"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I select "Redis" from dropdown "Engine"
    And I select "OnDemand" from dropdown "Pricing model"
    And I fill "Nodes" with "6"
    And I select "cache.r6g.large" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon ElastiCache" should be added successfully
    And a shareable estimate URL should be generated

  @integration @sqs @eu-region
  Scenario: Configure Amazon Simple Queue Service (SQS) - EU deployment
    Given I search for "Amazon Simple Queue Service (SQS)"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I fill "Standard queue requests" with "50000000"
    And I fill "FIFO queue requests" with "10000000"
    And I fill "Fair queue requests" with "5000000"
    And I click Save and add service
    Then the service "Amazon Simple Queue Service (SQS)" should be added successfully
    And a shareable estimate URL should be generated

  @security @guardduty @eu-region
  Scenario: Configure Amazon GuardDuty - EU deployment
    Given I search for "Amazon GuardDuty"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I fill "AWS CloudTrail Management Event Analysis" with "10000000"
    And I fill "EC2 VPC Flow Log Analysis" with "200"
    And I fill "EC2 DNS Query Log Analysis" with "100"
    And I fill "AWS CloudTrail S3 Data Event Analysis" with "20000000"
    And I click Save and add service
    Then the service "Amazon GuardDuty" should be added successfully
    And a shareable estimate URL should be generated

  @networking @route53 @resolver
  Scenario: Configure Amazon Route 53 - DNS Firewall and Resolver
    Given I search for "Amazon Route 53"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Hosted Zones" with "20"
    And I fill "Additional Records in Hosted Zones" with "1000"
    And I fill "Standard queries" with "100000000"
    And I fill "Latency based routing queries" with "10000000"
    And I fill "Geo DNS queries" with "5000000"
    And I fill "Number of Elastic Network Interfaces" with "10"
    And I fill "Recursive average DNS queries" with "50000000"
    And I fill "Number of domains stored" with "100"
    And I fill "DNS queries" with "10000000"
    And I click Save and add service
    Then the service "Amazon Route 53" should be added successfully
    And a shareable estimate URL should be generated

  @management @cloudwatch @eu-region
  Scenario: Configure Amazon CloudWatch - EU deployment
    Given I search for "Amazon CloudWatch"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I fill "Number of Metrics (includes detailed and custom metrics)" with "1000"
    And I fill "GetMetricData: Number of metrics requested" with "5000"
    And I fill "Number of other API requests" with "500000"
    And I click Save and add service
    Then the service "Amazon CloudWatch" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @athena @eu-region
  Scenario: Configure Amazon Athena - EU data lake queries
    Given I search for "Amazon Athena"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I fill "Total number of queries" with "5000"
    And I fill "Amount of data scanned per query" with "20"
    And I click Save and add service
    Then the service "Amazon Athena" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-lustre @hdd-archive
  Scenario: Configure Amazon FSx for Lustre - HDD archive storage
    Given I search for "Amazon FSx for Lustre"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "HDD" from dropdown "Storage type"
    And I fill "Storage capacity" with "12000"
    And I fill "Backup storage" with "5000"
    And I click Save and add service
    Then the service "Amazon FSx for Lustre" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-custom-oracle @ha
  Scenario: Configure Amazon RDS Custom for Oracle - HA deployment
    Given I search for "Amazon RDS Custom for Oracle"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of RDS Custom for Oracle instances" with "4"
    And I select "db.r6i.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "2000"
    And I click Save and add service
    Then the service "Amazon RDS Custom for Oracle" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-custom-sql @ha
  Scenario: Configure Amazon RDS Custom for SQL Server - HA deployment
    Given I search for "Amazon RDS Custom for SQL Server"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of RDS Custom for SQL Server instances" with "4"
    And I select "db.r6i.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "2000"
    And I click Save and add service
    Then the service "Amazon RDS Custom for SQL Server" should be added successfully
    And a shareable estimate URL should be generated

  @compute @app-runner @eu-region
  Scenario: Configure AWS App Runner - EU deployment
    Given I search for "AWS App Runner"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I fill "Concurrency" with "100"
    And I fill "Minimum provisioned container instances" with "3"
    And I fill "Peak traffic hours" with "10"
    And I fill "Number of requests during peak traffic (requests/second)" with "1000"
    And I fill "Number of requests during off-peak traffic (requests/second)" with "100"
    And I click Save and add service
    Then the service "AWS App Runner" should be added successfully
    And a shareable estimate URL should be generated

  @compute @ec2 @suse
  Scenario: Configure Amazon EC2 - SUSE Linux
    Given I search for "Amazon EC2"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "SUSE Linux Enterprise Server" from dropdown "Operating system"
    And I select "Shared Instances" from dropdown "Tenancy"
    And I fill "Number of instances" with "3"
    And I select "t3.xlarge" via autosuggest for "Search instance type"
    And I select "On-Demand" via radio button
    And I fill "Storage amount" with "100"
    And I click Save and add service
    Then the service "Amazon EC2" should be added successfully
    And a shareable estimate URL should be generated

  @database @rds-mariadb @io2-single
  Scenario: Configure Amazon RDS for MariaDB - Single-AZ io2
    Given I search for "Amazon RDS for MariaDB"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I select "Single-AZ" from dropdown "Deployment Option"
    And I select "Provisioned IOPS SSD (io2)" from dropdown "Storage type"
    And I fill "Nodes" with "1"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Storage amount" with "500"
    And I click Save and add service
    Then the service "Amazon RDS for MariaDB" should be added successfully
    And a shareable estimate URL should be generated

  @storage @fsx-openzfs @large
  Scenario: Configure Amazon FSx for OpenZFS - Large deployment
    Given I search for "Amazon FSx for OpenZFS"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Desired storage capacity" with "10240"
    And I click Save and add service
    Then the service "Amazon FSx for OpenZFS" should be added successfully
    And a shareable estimate URL should be generated

  @database @keyspaces @high-throughput
  Scenario: Configure Amazon Keyspaces - High throughput
    Given I search for "Amazon Keyspaces"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Storage" with "5000"
    And I fill "Number of writes" with "500000"
    And I fill "Number of reads" with "2000000"
    And I fill "Number of TTL delete operations" with "100000"
    And I click Save and add service
    Then the service "Amazon Keyspaces" should be added successfully
    And a shareable estimate URL should be generated

  @database @timestream @large
  Scenario: Configure Amazon Timestream - Enterprise time series
    Given I search for "Amazon Timestream"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Estimated Monthly Storage" with "10000"
    And I click Save and add service
    Then the service "Amazon Timestream" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @comprehend @enterprise
  Scenario: Configure Amazon Comprehend - Enterprise NLP
    Given I search for "Amazon Comprehend"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of documents asynchronous" with "5000000"
    And I fill "Average characters in a document asynchronous" with "5000"
    And I click Save and add service
    Then the service "Amazon Comprehend" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @textract @enterprise
  Scenario: Configure Amazon Textract - Enterprise document processing
    Given I search for "Amazon Textract"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of pages" with "5000000"
    And I fill "Percent of pages with text (Detect Document Text API) Enter %" with "95"
    And I click Save and add service
    Then the service "Amazon Textract" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @polly @enterprise
  Scenario: Configure Amazon Polly - Enterprise text-to-speech
    Given I search for "Amazon Polly"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of requests (Standard Text-to-Speech)" with "5000000"
    And I fill "Number of characters per request including white spaces, but excluding SSML" with "1000"
    And I click Save and add service
    Then the service "Amazon Polly" should be added successfully
    And a shareable estimate URL should be generated

  @ai-ml @translate @enterprise
  Scenario: Configure Amazon Translate - Enterprise translation
    Given I search for "Amazon Translate"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of characters including white spaces and punctuations (Standard Real-Time Translation)" with "500000000"
    And I click Save and add service
    Then the service "Amazon Translate" should be added successfully
    And a shareable estimate URL should be generated

  @storage @storage-gateway @enterprise
  Scenario: Configure AWS Storage Gateway - Enterprise hybrid storage
    Given I search for "AWS Storage Gateway"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Data written to AWS file storage by your gateway" with "5000"
    And I fill "Enter Amount" with "2000"
    And I click Save and add service
    Then the service "AWS Storage Gateway" should be added successfully
    And a shareable estimate URL should be generated

  @compute @gamelift-streams @large
  Scenario: Configure Amazon GameLift Streams - Large streaming deployment
    Given I search for "Amazon GameLift Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Estimated Daily Active Users" with "10000"
    And I fill "Estimated stream hours per user" with "3"
    And I click Save and add service
    Then the service "Amazon GameLift Streams" should be added successfully
    And a shareable estimate URL should be generated

  @security @verified-permissions @enterprise
  Scenario: Configure Amazon Verified Permissions - Enterprise authorization
    Given I search for "Amazon Verified Permissions"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Single Authorization Requests" with "50000000"
    And I fill "Number of Batch Authorization Requests" with "10000000"
    And I fill "Number of Policy Management Requests" with "100000"
    And I click Save and add service
    Then the service "Amazon Verified Permissions" should be added successfully
    And a shareable estimate URL should be generated

  @database @memorydb @eu-region
  Scenario: Configure Amazon MemoryDB - EU deployment
    Given I search for "Amazon MemoryDB"
    And I click Configure
    When I set the region to "EU (Ireland)"
    And I fill "Number of nodes" with "6"
    And I select "db.r6g.xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I fill "Data Written" with "200"
    And I fill "Snapshot storage" with "500"
    And I click Save and add service
    Then the service "Amazon MemoryDB" should be added successfully
    And a shareable estimate URL should be generated

  @compute @elastic-graphics @large
  Scenario: Configure Amazon Elastic Graphics - Large GPU workload
    Given I search for "Amazon Elastic Graphics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of nodes" with "8"
    And I select "eg1.4xlarge" via autosuggest for "Select an instance"
    And I fill "Utilization (On-Demand only)" with "100"
    And I click Save and add service
    Then the service "Amazon Elastic Graphics" should be added successfully
    And a shareable estimate URL should be generated

  @developer @codeguru @enterprise
  Scenario: Configure Amazon CodeGuru Reviewer - Enterprise code review
    Given I search for "Amazon CodeGuru Reviewer"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Total number of repositories" with "100"
    And I fill "Average lines of code (LOC) per repository" with "200000"
    And I click Save and add service
    Then the service "Amazon CodeGuru Reviewer" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-events @enterprise
  Scenario: Configure AWS IoT Events - Enterprise IoT monitoring
    Given I search for "AWS IoT Events"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices" with "10000"
    And I fill "Number of messages for a device including timer expiry messages" with "500"
    And I fill "Number of event detector models per device" with "5"
    And I fill "Average size of each message" with "2"
    And I fill "Number of actions triggered per message" with "2"
    And I click Save and add service
    Then the service "AWS IoT Events" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @glue @eu-region
  Scenario: Configure AWS Glue - EU data processing
    Given I search for "AWS Glue"
    And I click Configure
    When I set the region to "EU (Frankfurt)"
    And I fill "Number of DPUs for Apache Spark job" with "20"
    And I fill "Duration for which Apache Spark ETL job  runs" with "4"
    And I fill "Number of DPUs for Python Shell job" with "5"
    And I fill "Number of DPUs for each provisioned interactive session" with "10"
    And I click Save and add service
    Then the service "AWS Glue" should be added successfully
    And a shareable estimate URL should be generated

  @security @payment-cryptography @enterprise
  Scenario: Configure AWS Payment Cryptography - High volume transactions
    Given I search for "AWS Payment Cryptography"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of API requests" with "100000000"
    And I fill "Number of active keys" with "50"
    And I click Save and add service
    Then the service "AWS Payment Cryptography" should be added successfully
    And a shareable estimate URL should be generated

  @management @fis @enterprise
  Scenario: Configure AWS Fault Injection Service (FIS) - Enterprise chaos engineering
    Given I search for "AWS Fault Injection Service (FIS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Experiments per Month" with "100"
    And I fill "Average action-minutes per experiment" with "60"
    And I fill "Average count of target accounts per experiment" with "10"
    And I fill "% of Experiments per Month with experiment report Enter %" with "50"
    And I click Save and add service
    Then the service "AWS Fault Injection Service (FIS)" should be added successfully
    And a shareable estimate URL should be generated

  @management @audit-manager @enterprise
  Scenario: Configure AWS Audit Manager - Enterprise compliance
    Given I search for "AWS Audit Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of accounts" with "50"
    And I fill "Number of resources per account" with "1000"
    And I fill "Number of configuration snapshots (API calls)" with "50000"
    And I fill "Number of configuration changes/user activity logs (Cloudtrail)" with "100000"
    And I fill "Number of compliance checks (Security Hub, Config)" with "50000"
    And I click Save and add service
    Then the service "AWS Audit Manager" should be added successfully
    And a shareable estimate URL should be generated

  # ============================================================
  # COMPLETE FIELD COVERAGE SCENARIOS
  # (Services with fields not covered by scenarios above)
  # ============================================================

  @networking @route53 @full-coverage
  Scenario: Configure Amazon Route 53 - full health checks and routing
    Given I search for "Amazon Route 53"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Hosted Zones" with "10"
    And I fill "Additional Records in Hosted Zones" with "500"
    And I fill "Traffic Flow" with "5"
    And I fill "Standard queries" with "50000000"
    And I fill "Latency based routing queries" with "10000000"
    And I fill "Geo DNS queries" with "5000000"
    And I fill "IP-based routing queries" with "2000000"
    And I fill "IP (CIDR) blocks" with "50"
    And I fill "Basic Checks Within AWS" with "10"
    And I fill "Basic Checks Outside of AWS" with "5"
    And I fill "HTTPS Checks Within AWS" with "10"
    And I fill "HTTPS Checks Outside of AWS" with "5"
    And I fill "String Matching Checks Within AWS" with "5"
    And I fill "String Matching Checks Outside of AWS" with "3"
    And I fill "Fast Interval Checks Within AWS" with "5"
    And I fill "Fast Interval Checks Outside of AWS" with "3"
    And I fill "Latency Measurement Checks Within AWS" with "5"
    And I fill "Latency Measurement Checks Outside of AWS" with "3"
    And I fill "Number of Elastic Network Interfaces" with "10"
    And I fill "Recursive average DNS queries" with "5000000"
    And I fill "Number of domains stored" with "100"
    And I fill "DNS queries" with "10000000"
    And I fill "Number of VPCs associated to the rule group" with "5"
    And I fill "Number of hours the rule group is associated for" with "730"
    And I click Save and add service
    Then the service "Amazon Route 53" should be added successfully
    And a shareable estimate URL should be generated

  @security @guardduty @full-coverage
  Scenario: Configure Amazon GuardDuty - complete runtime and malware protection
    Given I search for "Amazon GuardDuty"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "AWS CloudTrail Management Event Analysis" with "50"
    And I fill "EC2 VPC Flow Log Analysis" with "1000"
    And I fill "EC2 DNS Query Log Analysis" with "500"
    And I fill "AWS CloudTrail S3 Data Event Analysis" with "100"
    And I fill "Amazon EKS Audit Logs Analysis" with "50"
    And I fill "EBS Volume Data Scan Analysis" with "200"
    And I fill "Total Size of S3 Objects scanned per month" with "500"
    And I fill "Number of PUT requests monitored per month" with "5000000"
    And I fill "Enter the amount of data scanned from EBS snapshots per month" with "200"
    And I fill "Enter the amount of data scanned from EC2 AMI per month" with "100"
    And I fill "Enter the amount of data scanned from S3 Recovery Point per month" with "100"
    And I fill "RDS provisioned instance vCPU" with "64"
    And I fill "Aurora Serverless v2 instances ACUs" with "32"
    And I fill "Lambda VPC Flow Log Analysis" with "200"
    And I fill "Amazon EKS Runtime Monitoring Analysis" with "100"
    And I fill "Amazon ECS Runtime Monitoring Analysis" with "100"
    And I fill "Amazon EC2 Runtime Monitoring Analysis" with "100"
    And I click Save and add service
    Then the service "Amazon GuardDuty" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @kinesis-video @full-coverage
  Scenario: Configure Amazon Kinesis Video Streams - full streaming with WebRTC
    Given I search for "Amazon Kinesis Video Streams"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of devices" with "50"
    And I fill "Average bitrate" with "5"
    And I fill "Duration of video streamed to Amazon Kinesis Video Streams (per device)" with "12"
    And I fill "Duration of video playback over HLS or MPEG-DASH (per camera)" with "4"
    And I fill "Duration of video consumed by other applications (per camera)" with "2"
    And I fill "Average length of each WebRTC session (for live view)" with "30"
    And I fill "TURN Usage Enter the percentage" with "20"
    And I fill "Average retention for video" with "7"
    And I fill "Images extracted per camera (1080p resolution stream or lower)" with "1000"
    And I fill "Images extracted per camera (greater than 1080p resolution stream)" with "500"
    And I click Save and add service
    Then the service "Amazon Kinesis Video Streams" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @ses @full-coverage
  Scenario: Configure Amazon Simple Email Service (SES) - enterprise with dedicated IPs
    Given I search for "Amazon Simple Email Service (SES)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Open Ingress Endpoint(s)" with "3"
    And I fill "Number of Emails processed by Mail Manager" with "5000000"
    And I fill "Email messages sent from EC2" with "2000000"
    And I fill "Attachment data sent from EC2" with "500"
    And I fill "Email messages sent from email client" with "500000"
    And I fill "Attachment data sent from email client" with "100"
    And I fill "Email messages received" with "3000000"
    And I fill "Average size of email processed by Mail Manager" with "50"
    And I fill "Email message sent via dedicated IPs (managed)" with "1000000"
    And I fill "Number of dedicated IP(standard) addresses" with "3"
    And I fill "Gigabytes Inserted & Indexed" with "100"
    And I fill "Gigabytes Already Stored" with "500"
    And I click Save and add service
    Then the service "Amazon Simple Email Service (SES)" should be added successfully
    And a shareable estimate URL should be generated

  @devops @cloudtrail @full-coverage
  Scenario: Configure AWS CloudTrail - full logging with insights and network activity
    Given I search for "AWS CloudTrail"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of management events" with "10000000"
    And I fill "Management event trails" with "2"
    And I fill "Read management events" with "5000000"
    And I fill "Read management trails" with "1"
    And I fill "S3 operations" with "1000000"
    And I fill "S3 trails" with "1"
    And I fill "Lambda data events" with "500000"
    And I fill "Lambda trails" with "1"
    And I fill "Number of network activity events" with "2000000"
    And I fill "Network activity event trails" with "1"
    And I fill "Total number of management API calls (both read and write) to be analyzed for unusual activity" with "10000000"
    And I fill "Number of trails and/or event data stores where Insights events are enabled" with "2"
    And I fill "Data ingested - CloudTrail" with "500"
    And I fill "Data ingested - 7 year retention" with "100"
    And I fill "Data scanned using queries" with "200"
    And I click Save and add service
    Then the service "AWS CloudTrail" should be added successfully
    And a shareable estimate URL should be generated

  @security @inspector @full-coverage
  Scenario: Configure Amazon Inspector - full scanning with code analysis
    Given I search for "Amazon Inspector"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average* No. of EC2 instances scanned per month" with "100"
    And I fill "Total number of newly pushed container images per month" with "500"
    And I fill "Total number of automated rescans per image per month" with "4"
    And I fill "Average number of Lambda functions scanned in a month" with "200"
    And I fill "Total number of repositories" with "50"
    And I fill "Number of SAST periodic scans per repository per month" with "4"
    And I fill "Number of SCA periodc scans per repository per month" with "4"
    And I fill "Number of IaC periodic scans per repository per month" with "4"
    And I fill "Total Number of on-demand scans (across each scan-type including SAST, SCA and IaC) per repository per month" with "10"
    And I fill "Total number of change-based scans (across each scan-type including SAST, SCA, IaC) per repository per month (including pull request/merge request or push) Enter a number" with "20"
    And I click Save and add service
    Then the service "Amazon Inspector" should be added successfully
    And a shareable estimate URL should be generated

  @compute @lambda @full-coverage
  Scenario: Configure AWS Lambda - with SnapStart cold-starts
    Given I search for "AWS Lambda"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of requests" with "5000000"
    And I fill "Duration of each request (in ms)" with "100"
    And I fill "Amount of memory allocated" with "2048"
    And I fill "Amount of ephemeral storage allocated" with "1024"
    And I fill "Concurrency" with "50"
    And I fill "Duration of each provisioned request (in ms)" with "80"
    And I fill "Number of cold-starts (i.e. SnapStart restores)" with "10000"
    And I click Save and add service
    Then the service "AWS Lambda" should be added successfully
    And a shareable estimate URL should be generated

  @ml @lookout-vision @full-coverage
  Scenario: Configure Amazon Lookout for Vision - full production deployment
    Given I search for "Amazon Lookout for Vision"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of plants" with "3"
    And I fill "Number of production lines per plant" with "5"
    And I fill "Number of inspection points per production line" with "4"
    And I fill "Number of cameras per inspection point" with "2"
    And I fill "Time to train initial model (hours)" with "10"
    And I fill "Average number of model retrains per model per month" with "2"
    And I fill "Number of inference units" with "5"
    And I fill "Number of production shifts per day" with "3"
    And I fill "Production hours per shift" with "8"
    And I fill "Production days per month" with "22"
    And I click Save and add service
    Then the service "Amazon Lookout for Vision" should be added successfully
    And a shareable estimate URL should be generated

  @devops @prometheus @full-coverage
  Scenario: Configure Amazon Managed Service for Prometheus - full observability
    Given I search for "Amazon Managed Service for Prometheus"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Average active time series" with "100000"
    And I fill "Avg Collection Interval (in seconds)" with "15"
    And I fill "Retention Period (in days)" with "90"
    And I fill "Average Number of Dashboard users per day" with "20"
    And I fill "Number of Prometheus rules" with "200"
    And I fill "Average rule execution interval (in seconds)" with "60"
    And I fill "Average number of queries per day per dashboard user" with "50"
    And I fill "Average samples per query for Monitoring queries" with "10000"
    And I fill "Average samples per query for Alerting queries" with "5000"
    And I fill "Number of collectors" with "10"
    And I fill "Number of Samples collected" with "50000000"
    And I click Save and add service
    Then the service "Amazon Managed Service for Prometheus" should be added successfully
    And a shareable estimate URL should be generated

  @other @workspaces-apps @full-coverage
  Scenario: Configure Amazon WorkSpaces Applications - elastic fleet full config
    Given I search for "Amazon WorkSpaces Applications"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of users per month" with "100"
    And I fill "Number of working hours per day" with "8"
    And I fill "Instance Disk Volume size" with "50"
    And I fill "Days in week" with "5"
    And I fill "Peak duration (hours) per day" with "4"
    And I fill "Average off-peak concurrent users per hour" with "20"
    And I fill "Average peak concurrent users per hour" with "60"
    And I fill "Days in weekend" with "2"
    And I click Save and add service
    Then the service "Amazon WorkSpaces Applications" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediaconnect @full-coverage
  Scenario: Configure AWS Elemental MediaConnect - full flow with outputs
    Given I search for "AWS Elemental MediaConnect"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of running flows" with "5"
    And I fill "Flow utilization" with "80"
    And I fill "Number of outputs per flow" with "3"
    And I fill "Bitrate (Mbit per second)" with "20"
    And I fill "Running flow utilization" with "80"
    And I fill "Number of running outputs" with "10"
    And I fill "Running output utilization" with "70"
    And I fill "Enter Amount" with "100"
    And I click Save and add service
    Then the service "AWS Elemental MediaConnect" should be added successfully
    And a shareable estimate URL should be generated

  @iot @iot-sitewise @full-coverage
  Scenario: Configure AWS IoT SiteWise - enterprise industrial with egress
    Given I search for "AWS IoT SiteWise"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of daily measurements" with "1000000"
    And I fill "Number of tags or sensors" with "5000"
    And I fill "Cloud data availablity" with "90"
    And I fill "Buffer period" with "30"
    And I fill "Number of messages in response to egress API calls" with "500000"
    And I fill "Total computations of metrics and transforms" with "10000000"
    And I fill "Volume of data (GB)" with "500"
    And I fill "Count of monthly active users" with "50"
    And I fill "Cost of Egress from IoT Sitewise Pricing Tool" with "100"
    And I click Save and add service
    Then the service "AWS IoT SiteWise" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @finspace @full-coverage
  Scenario: Configure Amazon FinSpace Dataset Browser - all cluster sizes
    Given I search for "Amazon FinSpace Dataset Browser"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of users" with "20"
    And I fill "Size of data to be stored" with "500"
    And I fill "Total time spent: Small cluster (across all users)" with "200"
    And I fill "Total time spent: Medium cluster (across all users)" with "100"
    And I fill "Total time spent: Large cluster (across all users)" with "50"
    And I fill "Total time spent: X-Large cluster (across all users)" with "20"
    And I fill "Total time spent: XX-Large cluster (across all users)" with "10"
    And I click Save and add service
    Then the service "Amazon FinSpace Dataset Browser" should be added successfully
    And a shareable estimate URL should be generated

  @ml @fraud-detector @full-coverage
  Scenario: Configure Amazon Fraud Detector - all model types
    Given I search for "Amazon Fraud Detector"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Event data processed and stored" with "100"
    And I fill "Number of model versions" with "5"
    And I fill "Training time per model version in hours" with "10"
    And I fill "Number of active model versions" with "3"
    And I fill "Number of monthly predictions with Online Fraud Insights (OFI) model type" with "1000000"
    And I fill "Number of monthly predictions with Transaction Fraud Insights (TFI) model type" with "500000"
    And I fill "Number of monthly predictions with rules only (no ML model)" with "2000000"
    And I click Save and add service
    Then the service "Amazon Fraud Detector" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @sns @full-coverage
  Scenario: Configure Amazon Simple Notification Service (SNS) - with data scanning and Firehose
    Given I search for "Amazon Simple Notification Service (SNS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Requests" with "10000000"
    And I fill "HTTP/HTTPS Notifications" with "5000000"
    And I fill "EMAIL/EMAIL-JSON Notifications" with "100000"
    And I fill "SQS Notifications" with "5000000"
    And I fill "Amazon Web Services Lambda" with "2000000"
    And I fill "Amazon Kinesis Data Firehose" with "1000000"
    And I fill "Mobile Push Notifications" with "500000"
    And I fill "Enter Amount" with "50"
    And I fill "Publish and Delivery Message Scanning" with "5000000"
    And I fill "The amount of outbound payload data scanned per month" with "100"
    And I click Save and add service
    Then the service "Amazon Simple Notification Service (SNS)" should be added successfully
    And a shareable estimate URL should be generated

  @media @mediapackage @full-coverage
  Scenario: Configure AWS Elemental MediaPackage - with VOD and cache ratio
    Given I search for "AWS Elemental MediaPackage"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of inputs per channel" with "2"
    And I fill "Total duration of live streams per month" with "720"
    And I fill "Ingest bitrate per input (Mbit per second)" with "10"
    And I fill "Average Number of viewers per hour" with "1000"
    And I fill "Average bitrate per viewer (Mbit per second)" with "5"
    And I fill "Cache/hit ratio Enter cache/hit ratio as a pecentage" with "80"
    And I fill "Hours of VOD content watched" with "5000"
    And I fill "Average bitrate (Mbit per second)" with "8"
    And I click Save and add service
    Then the service "AWS Elemental MediaPackage" should be added successfully
    And a shareable estimate URL should be generated

  @networking @firewall-manager @full-coverage
  Scenario: Configure AWS Firewall Manager - with WAF and security groups
    Given I search for "AWS Firewall Manager"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of protection policy" with "5"
    And I fill "Number of aws account" with "10"
    And I fill "Number of Configuration items recorded" with "50000"
    And I fill "Number of Config rule evaluations" with "100000"
    And I fill "Number of AWS Network Firewall endpoints" with "4"
    And I fill "Usage per endpoint" with "730"
    And I fill "Data processed per month" with "500"
    And I fill "Number of Web Access Control Lists (Web ACLs) utilized" with "5"
    And I fill "Number of Rules added per Web ACL" with "20"
    And I fill "Number of domains stored" with "1000"
    And I fill "DNS queries" with "10000000"
    And I fill "Elastic Load Balancing (ELB) Usage" with "200"
    And I fill "Elastic IP Usage" with "50"
    And I fill "Number of Security groups" with "100"
    And I click Save and add service
    Then the service "AWS Firewall Manager" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @eventbridge @full-coverage
  Scenario: Configure Amazon EventBridge - with opt-in data events and same-account delivery
    Given I search for "Amazon EventBridge"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Size of the payload" with "10"
    And I fill "Number of AWS management events" with "5000000"
    And I fill "Number of AWS opt-in data events" with "2000000"
    And I fill "Number of custom events" with "10000000"
    And I fill "Number of partner events" with "1000000"
    And I fill "Number of events delivered to another event bus" with "500000"
    And I fill "Number of events delivered to a service in the same account" with "8000000"
    And I fill "Number of events delivered to a service in a different account" with "2000000"
    And I fill "Number of invocations" with "5000000"
    And I fill "Number of events" with "10000000"
    And I fill "Number of replayed events" with "1000000"
    And I fill "Number of requests" with "5000000"
    And I click Save and add service
    Then the service "Amazon EventBridge" should be added successfully
    And a shareable estimate URL should be generated

  @messaging @msk @full-coverage
  Scenario: Configure Amazon Managed Streaming for Apache Kafka (MSK) - with private connectivity
    Given I search for "Amazon Managed Streaming for Apache Kafka (MSK)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Kafka broker nodes" with "6"
    And I select "kafka.m5.large" via autosuggest for "Select an instance"
    And I fill "Storage per Broker" with "500"
    And I fill "Desired Provisioned Storage Throughput (MiBps)" with "250"
    And I fill "Number of authentication schemes configured for private connectivity" with "2"
    And I fill "Data processed for private connectivity" with "1000"
    And I fill "Enter Amount" with "200"
    And I click Save and add service
    Then the service "Amazon Managed Streaming for Apache Kafka (MSK)" should be added successfully
    And a shareable estimate URL should be generated

  @analytics @iot-analytics @full-coverage
  Scenario: Configure AWS IoT Analytics - with advanced queries
    Given I search for "AWS IoT Analytics"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of IoT devices (monthly)" with "1000"
    And I fill "Data generation by each device" with "100"
    And I fill "Number of data pipelines (monthly)" with "10"
    And I fill "Data queried per month" with "500"
    And I fill "Number of queries (monthly)" with "1000"
    And I fill "Data scanned per query" with "10"
    And I fill "Average ACU execution time" with "30"
    And I click Save and add service
    Then the service "AWS IoT Analytics" should be added successfully
    And a shareable estimate URL should be generated

  @security @private-ca @full-coverage
  Scenario: Configure AWS Private Certificate Authority - with OCSP
    Given I search for "AWS Private Certificate Authority"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Private CAs" with "3"
    And I fill "Number of general purpose mode private certificates issued" with "10000"
    And I fill "Number of certificates used with ACM-integrated services" with "5000"
    And I fill "Number of short lived certificate mode private certificates issued" with "50000"
    And I fill "Number of OCSP responses per Month" with "1000000"
    And I fill "Number of OCSP Queries per hour" with "5000"
    And I click Save and add service
    Then the service "AWS Private Certificate Authority" should be added successfully
    And a shareable estimate URL should be generated

  @networking @cloudfront @full-coverage
  Scenario: Configure Amazon CloudFront - with all plan tiers
    Given I search for "Amazon CloudFront"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Free Plan" with "0"
    And I fill "Pro Plan" with "2"
    And I fill "Business Plan" with "1"
    And I fill "Premium Plan" with "1"
    And I click Save and add service
    Then the service "Amazon CloudFront" should be added successfully
    And a shareable estimate URL should be generated

  @devops @cloudwatch @full-coverage
  Scenario: Configure Amazon CloudWatch - with Database Insights and ACUs
    Given I search for "Amazon CloudWatch"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of Metrics (includes detailed and custom metrics)" with "500"
    And I fill "GetMetricData: Number of metrics requested" with "100000"
    And I fill "GetMetricWidgetImage: Number of metrics requested" with "10000"
    And I fill "Number of other API requests" with "500000"
    And I fill "Number of vCPUs monitored by Database Insights" with "32"
    And I fill "Number of Aurora Capacity Units (ACUs) monitored by Database Insights" with "16"
    And I click Save and add service
    Then the service "Amazon CloudWatch" should be added successfully
    And a shareable estimate URL should be generated

  @storage @ebs @full-coverage
  Scenario: Configure Amazon Elastic Block Store (EBS) - with snapshot API
    Given I search for "Amazon Elastic Block Store (EBS)"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of volumes" with "10"
    And I fill "Average duration of volume" with "730"
    And I fill "Storage amount per volume" with "500"
    And I fill "Amount changed per snapshot" with "10"
    And I fill "Number of snapshots to restore" with "5"
    And I fill "Number of GetSnapshotBlock API requests" with "100000"
    And I click Save and add service
    Then the service "Amazon Elastic Block Store (EBS)" should be added successfully
    And a shareable estimate URL should be generated

  @ml @healthlake @full-coverage
  Scenario: Configure Amazon Healthlake - with REST-Hook notifications
    Given I search for "Amazon Healthlake"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Additional Data Storage" with "500"
    And I fill "Total Number Of Queries per Month" with "100000"
    And I fill "Number Of NLP Characters" with "50000000"
    And I fill "Exported Data per GB" with "100"
    And I fill "Number of notifications to Amazon EventBridge" with "50000"
    And I fill "Number of notifications to REST-Hook" with "50000"
    And I click Save and add service
    Then the service "Amazon Healthlake" should be added successfully
    And a shareable estimate URL should be generated

  @ml @rekognition @full-coverage
  Scenario: Configure Amazon Rekognition - with Image Properties API
    Given I search for "Amazon Rekognition"
    And I click Configure
    When I set the region to "US East (N. Virginia)"
    And I fill "Number of images processed with labels API calls per month" with "1000000"
    And I fill "Number of images processed with content moderation API calls per month" with "500000"
    And I fill "Number of images processed with detect text API calls per month" with "200000"
    And I fill "Number of images processed with celebrity API calls per month" with "100000"
    And I fill "Number of images processed with PPE detection API calls per month" with "300000"
    And I fill "Number of images processed with Image Properties API calls per month" with "200000"
    And I fill "Number of DetectFaces API calls per month" with "500000"
    And I click Save and add service
    Then the service "Amazon Rekognition" should be added successfully
    And a shareable estimate URL should be generated
