enum TaskStatus {
  Pending = 'pending',
  Initializing = 'initializing',
  Active = 'active',
  Completed = 'completed',
  Failed = 'failed',
  StartFailed = 'start failed',
  NoDockerImage = 'non-existing Docker image',
  Crashed = 'crashed',
  Killed = 'killed by user'
}

export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
}

export interface CreateTask {
  name: string;
  description: string;
  image: string;
  collaboration_id: number;
  databases: string[];
  organizations: Organization[];
}

interface Organization {
  id: number;
  input: string;
}

export interface CreateTaskInput {
  method: string;
  kwargs: Object;
}
