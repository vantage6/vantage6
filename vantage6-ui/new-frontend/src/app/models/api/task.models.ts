export interface BaseTask {
  id: number;
  name: string;
  description: string;
  status: TaskStatus;
}

enum TaskStatus {
  Pending = 'pending'
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
  master: boolean;
  method: string;
  kwargs: Object;
}
