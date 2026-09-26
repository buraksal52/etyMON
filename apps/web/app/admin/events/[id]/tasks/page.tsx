"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiRequest } from "../../../../../lib/api";

type PythonGate = { prompt: string; answers: string[] };

type Task = {
  id: string;
  title: string;
  description: string;
  instructions: string;
  points: number;
  rewardAmount: string | null;
  rewardToken: string;
  proofType: string;
  active: boolean;
  metadata: Record<string, unknown> | null;
};

const PROOF_TYPES = ["TEXT", "URL", "TEXT_OR_URL", "IMAGE", "IMAGE_AND_URL"];
// The participant flow has three stages; stages 1 and 2 unlock the next one
// with a Python question (see docs/mission-pool.md).
const FINAL_STAGE = 3;

function readStage(task: Task): number | null {
  const stage = task.metadata?.missionStage;
  return typeof stage === "number" ? stage : null;
}

function readGate(task: Task): PythonGate {
  const gate = task.metadata?.pythonGate as Partial<PythonGate> | undefined;
  return {
    prompt: typeof gate?.prompt === "string" ? gate.prompt : "",
    answers: Array.isArray(gate?.answers) ? gate.answers : [],
  };
}

export default function TaskManagementPage() {
  const params = useParams<{ id: string }>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [points, setPoints] = useState("10");
  const [proofType, setProofType] = useState("TEXT");
  const [rewardAmount, setRewardAmount] = useState("");
  const [missionStage, setMissionStage] = useState("1");
  const [pythonPrompt, setPythonPrompt] = useState("");
  const [pythonAnswers, setPythonAnswers] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingMetadata, setEditingMetadata] = useState<Record<
    string,
    unknown
  > | null>(null);
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
    setRewardAmount("");
    setMissionStage("1");
    setPythonPrompt("");
    setPythonAnswers("");
    setEditingId(null);
    setEditingMetadata(null);
  }

  function edit(task: Task) {
    setEditingId(task.id);
    setTitle(task.title);
    setDescription(task.description);
    setInstructions(task.instructions);
    setPoints(String(task.points));
    setProofType(task.proofType);
    setRewardAmount(task.rewardAmount ? String(Number(task.rewardAmount)) : "");
    setMissionStage(String(readStage(task) ?? 1));
    const gate = readGate(task);
    setPythonPrompt(gate.prompt);
    setPythonAnswers(gate.answers.join("\n"));
    setEditingMetadata(task.metadata);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const stage = Number(missionStage);
      const metadata: Record<string, unknown> = {
        ...(editingMetadata ?? {}),
        missionStage: stage,
      };
      if (stage < FINAL_STAGE) {
        metadata.pythonGate = {
          prompt: pythonPrompt.trim(),
          answers: pythonAnswers
            .split("\n")
            .map((answer) => answer.trim())
            .filter(Boolean),
        };
      } else {
        delete metadata.pythonGate;
      }
      const payload = {
        title,
        description,
        instructions,
        points: Number(points),
        proof_type: proofType,
        reward_amount: rewardAmount.trim() ? rewardAmount.trim() : null,
        metadata,
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
          <label>
            Proof type
            <select
              value={proofType}
              onChange={(event) => setProofType(event.target.value)}
            >
              {PROOF_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Mission stage
            <select
              value={missionStage}
              onChange={(event) => setMissionStage(event.target.value)}
            >
              {[1, 2, 3].map((stage) => (
                <option key={stage} value={stage}>
                  Stage {stage}
                </option>
              ))}
            </select>
          </label>
          {Number(missionStage) < FINAL_STAGE && (
            <>
              <label>
                Python question (unlocks stage {Number(missionStage) + 1})
                <textarea
                  value={pythonPrompt}
                  onChange={(event) => setPythonPrompt(event.target.value)}
                  placeholder="e.g. What does print(2 ** 3) output?"
                />
              </label>
              <label>
                Accepted answers (one per line, case-sensitive)
                <textarea
                  value={pythonAnswers}
                  onChange={(event) => setPythonAnswers(event.target.value)}
                  placeholder="8"
                />
              </label>
            </>
          )}
          <label>
            MON reward on approval (optional)
            <input
              type="number"
              min="0"
              step="any"
              value={rewardAmount}
              onChange={(event) => setRewardAmount(event.target.value)}
              placeholder="No on-chain reward"
            />
          </label>
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
                <p className="eyebrow">
                  {task.active ? "ACTIVE" : "INACTIVE"} ·{" "}
                  {readStage(task)
                    ? `STAGE ${readStage(task)}`
                    : "NO STAGE (never assigned)"}
                </p>
                <h2>{task.title}</h2>
              </div>
              <span className="points">
                +{task.points} pts
                {task.rewardAmount &&
                  ` · ${Number(task.rewardAmount)} ${task.rewardToken}`}
              </span>
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
