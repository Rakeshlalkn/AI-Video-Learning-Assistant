export type User = {
  id: string;
  name: string;
  email: string;
  profile_image?: string | null;
  created_at: string;
};

export type VideoStatus = "pending" | "processing" | "ready" | "failed";

export type Video = {
  id: number;
  user_id: string;
  title: string;
  file_path: string;
  source_type: "upload" | "youtube";
  source_url?: string | null;
  transcript?: string | null;
  status: VideoStatus;
  progress?: string | null;
  progress_pct?: number;
  error_message?: string | null;
  created_at: string;
};

export type VideoSummary = {
  id: number;
  title: string;
  status: VideoStatus;
  source_type: "upload" | "youtube";
  progress?: string | null;
  progress_pct?: number;
  created_at: string;
};

export type DocumentType = "notes" | "chat";

export type DocumentRecord = {
  id: number;
  video_id: number;
  title: string;
  content: string;
  doc_type: DocumentType;
  created_at: string;
  updated_at: string;
};

export type DashboardResponse = {
  total_videos: number;
  total_documents: number;
  ready_videos: number;
  recent: VideoSummary[];
};

export type ChatResponse = {
  answer: string;
  sources: string[];
};
