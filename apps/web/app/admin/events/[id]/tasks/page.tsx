"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiRequest } from "../../../../../lib/api";

type Task = {
  id: string;
  title: string;
  description: string;
  instructions: string;
  points: number;
  proofType: string;
  active: boolean;
};

export default function TaskManagementPage() {
  const params = useParams<{ id: string }>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [points, setPoints] = useState("10");
  const [proofType, setProofType] = useState("TEXT");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const result = await apiRequest<{ tasks: Task[] }>(
        `/admin/events/${params.id}/tasks`,
      );
      setTasks(result.tasks);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load tasks",
      );
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  function resetForm() {
    setTitle("");
    setDescription("");
    setInstructions("");
    setPoints("10");
    setProofType("TEXT");
    setEditingId(null);
  }

  function edit(task: Task) {
    setEditingId(task.id);
    setTitle(task.title);
    setDescription(task.description);
    setInstructions(task.instructions);
    setPoints(String(task.points));
    setProofType(task.proofType);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload = {
        title,
        description,
        instructions,
        points: Number(points),
        proof_type: proofType,
      };
      await apiRequest(
        editingId
          ? `/admin/tasks/${editingId}`
          : `/admin/events/${params.id}/tasks`,
        {
          method: editingId ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      resetForm();
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to create task",
      );
    }
  }

  async function toggle(task: Task) {
    await apiRequest(`/admin/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !task.active }),
    });
    await load();
  }

  async function remove(task: Task) {
    if (!window.confirm(`Delete ${task.title}?`)) return;
    await apiRequest(`/admin/tasks/${task.id}`, { method: "DELETE" });
    await load();
  }

  return (
    <main className="screen admin-screen">
      <section className="card">
        <p className="eyebrow">Task management</p>
        <h1>{editingId ? "Edit task" : "Create task"}</h1>
        <form onSubmit={save} className="proof-form">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Title"
            required
          />
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description"
            required
          />
          <textarea
            value={instructions}
            onChange={(event) => setInstructions(event.target.value)}
            placeholder="Instructions"
            required
          />
          <input
            type="number"
            min="1"
            value={points}
            onChange={(event) => setPoints(event.target.value)}
            required
          />
          <input
            value={proofType}
            onChange={(event) => setProofType(event.target.value)}
            placeholder="Proof type"
            required
          />
          <button type="submit">
            {editingId ? "Save changes" : "Create task"}
          </button>
          {editingId && (
            <button
              type="button"
              className="secondary-button"
              onClick={resetForm}
            >
              Cancel edit
            </button>
          )}
        </form>
        {error && <p className="error">{error}</p>}
      </section>
      <section className="submission-list">
        {tasks.map((task) => (
          <article className="card submission-card" key={task.id}>
            <div className="submission-meta">
              <div>
                <p className="eyebrow">{task.active ? "ACTIVE" : "INACTIVE"}</p>
                <h2>{task.title}</h2>
              </div>
              <span className="points">+{task.points} pts</span>
            </div>
            <p>{task.description}</p>
            <div className="review-actions">
              <button type="button" onClick={() => edit(task)}>
                Edit
              </button>
              <button type="button" onClick={() => void toggle(task)}>
                {task.active ? "Deactivate" : "Activate"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void remove(task)}
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
