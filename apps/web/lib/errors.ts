import { ApiError } from "./api";

const MESSAGES: Record<string, string> = {
  "Network error":
    "Sunucuya ulaşılamıyor. İnternet bağlantınızı kontrol edip tekrar deneyin.",
  "Request failed": "İstek tamamlanamadı. Lütfen tekrar deneyin.",
  "Invalid organizer credentials": "E-posta veya şifre hatalı.",
  "Too many login attempts":
    "Çok fazla giriş denemesi yapıldı. Bir dakika bekleyip tekrar deneyin.",
  "Too many join attempts":
    "Çok fazla katılım denemesi yapıldı. Bir dakika bekleyip tekrar deneyin.",
  "Organizer session required":
    "Oturumunuz bulunamadı. Lütfen yeniden giriş yapın.",
  "Invalid organizer session":
    "Oturumunuzun süresi doldu. Lütfen yeniden giriş yapın.",
  "Participant session required":
    "Oturumunuz bulunamadı. Lütfen event'e tekrar katılın.",
  "Invalid participant session":
    "Oturumunuzun süresi doldu. Lütfen event'e tekrar katılın.",
  "Invalid session": "Oturum geçersiz. Lütfen event'e tekrar katılın.",
  "Event session mismatch":
    "Oturumunuz bu event'e ait değil. Lütfen event'e tekrar katılın.",
  "Event not found": "Event bulunamadı. Event code'u kontrol edin.",
  "Event slug already exists":
    "Bu event code zaten kullanılıyor. Başka bir slug seçin.",
  "Event is not accepting entries":
    "Bu event şu anda katılım kabul etmiyor.",
  "Participant is blocked": "Bu event'e katılımınız engellenmiş.",
  "Participant is not eligible": "Bu event için uygun görünmüyorsunuz.",
  "Event is not active": "Event şu anda aktif değil.",
  "Task deadline has passed": "Görev süresi sona erdi.",
  "Submission deadline has passed": "Gönderim süresi sona erdi.",
  "Participant already has an unresolved task":
    "Çözülmemiş bir görevin var. Yeni görev için önce onu tamamlamalısın.",
  "No task is currently available": "Şu anda atanabilecek bir görev yok.",
  "Assigned task not found": "Atanan görev bulunamadı.",
  "Assignment not found": "Görev ataması bulunamadı.",
  "Assignment does not belong to participant":
    "Bu görev size ait görünmüyor.",
  "Assignment is not available for submission":
    "Bu görev için artık kanıt gönderilemez.",
  "Image proof is required": "Fotoğraf kanıtı zorunlu.",
  "URL proof is required": "URL kanıtı zorunlu.",
  "Text proof is required": "Metin kanıtı zorunlu.",
  "Image and URL proof are required": "Fotoğraf ve URL kanıtı zorunlu.",
  "Text or URL proof is required": "Metin veya URL kanıtı zorunlu.",
  "Unsupported proof file type":
    "Desteklenmeyen dosya türü. JPEG, PNG, WebP veya PDF yükleyin.",
  "Proof file is too large": "Dosya çok büyük.",
  "Unsupported receipt file type":
    "Desteklenmeyen dosya türü. JPEG, PNG, WebP veya PDF yükleyin.",
  "Receipt file is too large": "Fiş dosyası çok büyük.",
  "File content does not match its MIME type":
    "Dosya içeriği seçilen dosya türüyle uyuşmuyor.",
  "Amount must be a valid number": "Tutar geçerli bir sayı olmalı.",
  "Amount must be zero or greater": "Tutar sıfır veya daha büyük olmalı.",
  "Currency must be a 3-letter code": "Para birimi 3 harfli olmalı (örn. TRY).",
  "Event cannot be edited after start":
    "Event başladıktan sonra düzenlenemez.",
  "Invalid event state transition": "Bu durum geçişi yapılamaz.",
  "Event cannot be started from its current state":
    "Event mevcut durumundan başlatılamaz.",
  "Event cannot be ended from its current state":
    "Event mevcut durumundan bitirilemez.",
  "Event has no active tasks":
    "Aktif görev olmadan event başlatılamaz. Önce görev havuzunu doldurun.",
  "Tasks cannot be edited after start":
    "Event başladıktan sonra görevler düzenlenemez.",
  "Tasks cannot be created after start":
    "Event başladıktan sonra görev eklenemez.",
  "Assigned tasks cannot be deleted":
    "Katılımcılara atanmış görevler silinemez. Bunun yerine pasif yapın.",
  "Task not found": "Görev bulunamadı.",
  "Submission not found": "Gönderim bulunamadı.",
  "Submission was already reviewed": "Bu gönderim zaten incelenmiş.",
  "Assignment is not reviewable": "Bu gönderim incelenemez durumda.",
  "Reimbursement not found": "Masraf kaydı bulunamadı.",
  "Reimbursement is not awaiting review": "Bu masraf zaten incelenmiş.",
  "Only approved reimbursements can be marked paid":
    "Yalnızca onaylanmış masraflar ödendi olarak işaretlenebilir.",
  "File not found": "Dosya bulunamadı.",
  "File access denied": "Bu dosyaya erişim izniniz yok.",
};

export function describeError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.message] ?? error.message ?? fallback;
  }
  return fallback;
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
