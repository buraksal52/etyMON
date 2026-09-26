"use client";

import { ChangeEvent, FormEvent, useState } from "react";

type ProofFormProps = {
  proofType: string;
  onSubmit: (proof: { file?: File; text?: string; url?: string }) => void;
  disabled?: boolean;
};

export function ProofForm({
  proofType,
  onSubmit,
  disabled = false,
}: ProofFormProps) {
  const [file, setFile] = useState<File>();
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0]);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ file, text: text || undefined, url: url || undefined });
  }

  const needsFile = proofType === "IMAGE" || proofType === "IMAGE_AND_URL";
  const needsUrl =
    proofType === "URL" ||
    proofType === "IMAGE_AND_URL" ||
    proofType === "TEXT_OR_URL";
  const needsText = proofType === "TEXT" || proofType === "TEXT_OR_URL";

  return (
    <form className="proof-form" onSubmit={handleSubmit}>
      {needsFile && (
        <label>
          Photo proof
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            required
          />
        </label>
      )}
      {needsUrl && (
        <label>
          URL proof
          <input
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            required
          />
        </label>
      )}
      {needsText && (
        <label>
          Text proof
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            required
          />
        </label>
      )}
      <button type="submit" disabled={disabled}>
        Submit proof
      </button>
    </form>
  );
}
