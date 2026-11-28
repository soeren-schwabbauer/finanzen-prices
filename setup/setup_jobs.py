# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Setup Jobs
# MAGIC Create or update Lakeflow Jobs from `config/jobs.yaml`.
# MAGIC Existing job settings are replaced; jobs removed from YAML are not deleted.

# COMMAND ----------

import yaml
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs

w = WorkspaceClient()

# COMMAND ----------

PROJECT_ROOT = Path.cwd().parent
CONFIG_PATH = PROJECT_ROOT / 'config' / 'jobs.yaml'
with CONFIG_PATH.open(encoding='utf-8') as file:
    config = yaml.safe_load(file)
JOB_CONFIG = config['jobs']
print(f'Project root: {PROJECT_ROOT}')
print(f'Configured jobs: {len(JOB_CONFIG)}')

# COMMAND ----------

def build_job_settings(job_key, cfg):
    notebook_path = str(PROJECT_ROOT / cfg['notebook']).removeprefix('/Workspace')
    w.workspace.get_status(notebook_path)
    return jobs.JobSettings(
        name=cfg['name'],
        tasks=[jobs.Task(
            task_key=job_key,
            notebook_task=jobs.NotebookTask(
                notebook_path=notebook_path,
                source=jobs.Source.WORKSPACE,
            ),
            max_retries=cfg.get('max_retries', 0),
            timeout_seconds=cfg.get('timeout_seconds', 600),
        )],
        schedule=jobs.CronSchedule(
            quartz_cron_expression=cfg['schedule']['cron'],
            timezone_id=cfg['schedule']['timezone'],
            pause_status=(jobs.PauseStatus.UNPAUSED if cfg['schedule']['enabled'] else jobs.PauseStatus.PAUSED),
        ),
        max_concurrent_runs=cfg.get('max_concurrent_runs', 1),
        queue=jobs.QueueSettings(enabled=True),
        tags=cfg.get('tags', {}),
    )

# COMMAND ----------

def create_or_update_job(settings):
    existing = [j for j in w.jobs.list(name=settings.name) if j.settings and j.settings.name == settings.name]
    if len(existing) > 1:
        raise RuntimeError(f'Multiple jobs found: {settings.name}')
    if existing:
        job_id = existing[0].job_id
        w.jobs.reset(job_id=job_id, new_settings=settings)
        print(f'Updated: {settings.name}')
    else:
        result = w.jobs.create(
            name=settings.name, tasks=settings.tasks, schedule=settings.schedule,
            max_concurrent_runs=settings.max_concurrent_runs,
            queue=settings.queue, tags=settings.tags,
        )
        job_id = result.job_id
        print(f'Created: {settings.name}')
    return job_id

# COMMAND ----------

# Validate notebook paths before changing any jobs.
settings_by_key = {key: build_job_settings(key, cfg) for key, cfg in JOB_CONFIG.items()}
if len({s.name for s in settings_by_key.values()}) != len(settings_by_key):
    raise ValueError('Job names must be unique in jobs.yaml')

deployed_jobs = {}
for key, settings in settings_by_key.items():
    job_id = create_or_update_job(settings)
    deployed_jobs[key] = job_id
    print(f'URL: {w.config.host}/#job/{job_id}')

# COMMAND ----------

for key, job_id in deployed_jobs.items():
    job = w.jobs.get(job_id=job_id)
    print(f'Name: {job.settings.name}')
    print(f'ID: {job_id}')
    print(f'Cron: {job.settings.schedule.quartz_cron_expression}')
    print(f'Timezone: {job.settings.schedule.timezone_id}')
    print(f'Status: {job.settings.schedule.pause_status}')
    print('-' * 50)