# Healthcheck Project

This project focuses on performing health checks on various CMTS (Cable Modem Termination System) devices from different vendors using Ansible playbooks.

## File Structure

```markdown
Healthcheck/
├── CMTS_Healthcheck_Dag.py
└── playbooks/
    ├── vendor1_pb.yml
    ├── vendor2_pb.yml
    ├── vendor3_pb.yml
    └── commands/
        ├── vendor1_R1_cmts_summary_short.output
        ├── vendor1_R2_cmts_summary_short.output
        ├── vendor2_R1_cmts_summary_short.output
        ├── vendor2_R2_cmts_summary_short.output
        ├── vendor2_R3_cmts_summary_short.output
        ├── vendor3_R1_cmts_summary_short.output
        ├── vendor3_R2_cmts_summary_short.output
        └── templates/
            ├── variables.j2
            ├── vendor1_cmts_summary.template
            ├── vendor2_cmts_summary.template
            └── vendor3_cmts_summary.template

CMTS_Healthcheck_Dag.py: The Airflow DAG file responsible for orchestrating the health check tasks.

playbooks/: This directory contains Ansible playbooks for each vendor.

  vendor1_pb.yml: Ansible playbook for vendor 1.
  vendor2_pb.yml: Ansible playbook for vendor 2.
  vendor3_pb.yml: Ansible playbook for vendor 3.

commands/: This directory contains output files generated when running specific commands on the CMTS devices.
    Short summary output files for each vendor.

templates/: This directory contains Jinja2 templates for generating JSON variable files.
    variables.j2: Template for JSON variables to be used by Ansible playbooks.
    CMTS summary templates for each vendor.


```

## Usage

```markdown
Make sure you have Ansible installed on your system.
Update the playbook files with the necessary configurations for your environment.
Execute the Airflow DAG CMTS_Healthcheck_Dag.py to perform the health checks.
Review the output generated in the commands directory for each vendor.

```

## Data visualization

```markdown
The collected data is uploaded to InfluxDB for storage and visualization. Grafana can then be used to create dashboards and graphs based on this data.

```

## Contributions

```markdown
Contributions are welcome! If you have suggestions or improvements, feel free to open an issue or create a pull request.
```
