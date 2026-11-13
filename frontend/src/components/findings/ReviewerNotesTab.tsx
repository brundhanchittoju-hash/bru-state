import React, { useState } from "react";
import { MessageSquare, CornerDownRight, Edit2, Trash2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ReviewerNotesTabProps {
  notes: any[];
  currentUserId?: string;
  onAddNote: (content: string, parentId?: string) => Promise<void>;
  onEditNote: (noteId: string, content: string) => Promise<void>;
  onDeleteNote: (noteId: string) => Promise<void>;
  isLocked?: boolean;
}

export const ReviewerNotesTab: React.FC<ReviewerNotesTabProps> = ({
  notes,
  onAddNote,
  onEditNote,
  onDeleteNote,
  isLocked = false,
}) => {
  const [newNoteContent, setNewNoteContent] = useState("");
  const [replyParentId, setReplyParentId] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePostNote = async () => {
    if (!newNoteContent.trim()) return;
    setIsSubmitting(true);
    try {
      await onAddNote(newNoteContent.trim());
      setNewNoteContent("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePostReply = async (parentId: string) => {
    if (!replyContent.trim()) return;
    setIsSubmitting(true);
    try {
      await onAddNote(replyContent.trim(), parentId);
      setReplyContent("");
      setReplyParentId(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveEdit = async (noteId: string) => {
    if (!editContent.trim()) return;
    setIsSubmitting(true);
    try {
      await onEditNote(noteId, editContent.trim());
      setEditingNoteId(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Group top-level notes and replies
  const topLevelNotes = notes.filter((n) => !n.parent_id);
  const repliesByParent = notes.reduce((acc: Record<string, any[]>, n) => {
    if (n.parent_id) {
      acc[n.parent_id] = acc[n.parent_id] || [];
      acc[n.parent_id].push(n);
    }
    return acc;
  }, {});

  return (
    <div className="space-y-4 text-xs">
      {/* Top note input */}
      {!isLocked && (
        <div className="border border-border rounded-xl p-3.5 bg-card space-y-2.5">
          <label className="font-semibold text-foreground flex items-center gap-1.5">
            <MessageSquare className="h-4 w-4 text-primary" />
            <span>Add Reviewer Discussion Note</span>
          </label>
          <textarea
            value={newNoteContent}
            onChange={(e) => setNewNoteContent(e.target.value)}
            placeholder="Document observations, audit inquiries, or cross-checks..."
            rows={2}
            className="w-full text-xs p-2.5 border border-input rounded-lg bg-muted/40 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="flex justify-end">
            <Button
              size="sm"
              disabled={isSubmitting || !newNoteContent.trim()}
              onClick={handlePostNote}
              className="h-7 text-xs"
            >
              <Send className="h-3 w-3 mr-1" />
              Post Note
            </Button>
          </div>
        </div>
      )}

      {/* Notes List */}
      <div className="space-y-3">
        {topLevelNotes.length === 0 ? (
          <p className="text-center text-muted-foreground py-6">No reviewer notes posted yet.</p>
        ) : (
          topLevelNotes.map((note) => {
            const replies = repliesByParent[note.id] || [];
            const isEditing = editingNoteId === note.id;

            return (
              <div
                key={note.id}
                className="border border-border rounded-xl p-3.5 bg-card space-y-2"
              >
                {/* Note Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-foreground">
                      {note.author_name}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted font-mono text-muted-foreground">
                      {note.author_role}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono tabular-nums">
                      {new Date(note.created_at).toLocaleString()}
                    </span>
                    {note.edited_at && (
                      <span className="text-[9px] text-muted-foreground italic">(edited)</span>
                    )}
                  </div>
                  {!isLocked && (
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingNoteId(note.id);
                          setEditContent(note.content);
                        }}
                        className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                      >
                        <Edit2 className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onDeleteNote(note.id)}
                        className="h-6 w-6 p-0 text-rose-500 hover:text-rose-600"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </div>

                {/* Note Content */}
                {isEditing ? (
                  <div className="space-y-2 pt-1">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={2}
                      className="w-full text-xs p-2 border border-input rounded-lg bg-muted/40 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <div className="flex gap-2 justify-end">
                      <Button size="sm" variant="outline" className="h-6 text-[10px]" onClick={() => setEditingNoteId(null)}>
                        Cancel
                      </Button>
                      <Button size="sm" className="h-6 text-[10px]" onClick={() => handleSaveEdit(note.id)}>
                        Save
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-foreground/90 leading-relaxed font-sans">
                    {note.content}
                  </p>
                )}

                {/* Reply Toggle */}
                {!isLocked && (
                  <div className="flex items-center justify-between pt-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setReplyParentId(replyParentId === note.id ? null : note.id)}
                      className="text-[11px] h-6 px-1.5 text-primary hover:text-primary/80"
                    >
                      <CornerDownRight className="h-3 w-3 mr-1" />
                      Reply
                    </Button>
                  </div>
                )}

                {/* Reply Input Box */}
                {replyParentId === note.id && (
                  <div className="pl-4 border-l-2 border-primary pt-2 space-y-1.5">
                    <textarea
                      value={replyContent}
                      onChange={(e) => setReplyContent(e.target.value)}
                      placeholder="Write your threaded reply..."
                      rows={2}
                      className="w-full text-xs p-2 border border-input rounded-lg bg-muted/40 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <div className="flex justify-end gap-1.5">
                      <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => setReplyParentId(null)}>
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        disabled={isSubmitting || !replyContent.trim()}
                        onClick={() => handlePostReply(note.id)}
                        className="h-6 text-[10px]"
                      >
                        Reply
                      </Button>
                    </div>
                  </div>
                )}

                {/* Nested Replies */}
                {replies.length > 0 && (
                  <div className="pl-4 border-l-2 border-border space-y-2 mt-2">
                    {replies.map((reply) => (
                      <div key={reply.id} className="bg-muted/40 p-2.5 rounded-lg border border-border/60 text-xs space-y-1">
                        <div className="flex justify-between items-center text-[10px] text-muted-foreground">
                          <span className="font-semibold text-foreground">
                            {reply.author_name} ({reply.author_role})
                          </span>
                          <span className="font-mono tabular-nums">{new Date(reply.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-foreground/90 font-sans">{reply.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
