from kubernetes import client, config
from src.config import settings
import json

class K8sService:
    def __init__(self):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        self.batch_v1 = client.BatchV1Api()
        self.namespace = settings.KUBERNETES_NAMESPACE

    def create_cronjob(self, name: str, schedule: str, image: str, env_vars: dict):
        container = client.V1Container(
            name="worker",
            image=image,
            image_pull_policy="Always",
            env=[client.V1EnvVar(name=k, value=v) for k, v in env_vars.items()]
        )
        
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": f"opentrack-{name}"}),
            spec=client.V1PodSpec(restart_policy="OnFailure", containers=[container])
        )
        
        cron_job_spec = client.V1CronJobSpec(
            schedule=schedule,
            concurrency_policy="Forbid",
            job_template=client.V1JobTemplateSpec(
                spec=client.V1JobSpec(
                    template=template,
                    backoff_limit=4
                )
            )
        )
        
        cron_job = client.V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=client.V1ObjectMeta(name=name),
            spec=cron_job_spec
        )
        
        return self.batch_v1.create_namespaced_cron_job(
            namespace=self.namespace,
            body=cron_job
        )

    def delete_cronjob(self, name: str):
        try:
            return self.batch_v1.delete_namespaced_cron_job(
                name=name,
                namespace=self.namespace
            )
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise e

    def suspend_cronjob(self, name: str, suspend: bool = True):
        body = {"spec": {"suspend": suspend}}
        return self.batch_v1.patch_namespaced_cron_job(
            name=name,
            namespace=self.namespace,
            body=body
        )

    def trigger_job(self, cronjob_name: str):
        # Get the CronJob to copy its job template for immediate execution
        cronjob = self.batch_v1.read_namespaced_cron_job(
            name=cronjob_name,
            namespace=self.namespace
        )
        
        import uuid
        job_name = f"{cronjob_name}-manual-{uuid.uuid4().hex[:6]}"
        
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                labels={"cronjob-name": cronjob_name}
            ),
            spec=cronjob.spec.job_template.spec
        )
        
        return self.batch_v1.create_namespaced_job(
            namespace=self.namespace,
            body=job
        )

    def get_job_executions(self, cronjob_name: str):
        # List jobs in the namespace and filter by owner or label to track history
        jobs = self.batch_v1.list_namespaced_job(namespace=self.namespace)
        
        executions = []
        for job in jobs.items:
            # Check if it was created by the CronJob or by our manual trigger
            is_ours = False
            if job.metadata.labels and job.metadata.labels.get("cronjob-name") == cronjob_name:
                is_ours = True
            elif job.metadata.owner_references:
                for owner in job.metadata.owner_references:
                    if owner.kind == "CronJob" and owner.name == cronjob_name:
                        is_ours = True
                        break
            
            if is_ours:
                executions.append({
                    "name": job.metadata.name,
                    "status": "succeeded" if job.status.succeeded else "failed" if job.status.failed else "running",
                    "start_time": job.status.start_time,
                    "completion_time": job.status.completion_time
                })
        
        # Sort by start time descending
        executions.sort(key=lambda x: x["start_time"] if x["start_time"] else 0, reverse=True)
        return executions

k8s_service = K8sService()
