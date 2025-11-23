# Clean Architecture - AI Summary System

## البنية المعمارية

تم إعادة هيكلة النظام باستخدام **Clean Architecture** لضمان:
- قابلية الصيانة والتوسعة
- فصل الاهتمامات (Separation of Concerns)
- سهولة الاختبار
- استقلالية الطبقات

## هيكل المشروع

```
back-end/
├── domain/              # Domain Layer (Core Business Logic)
│   ├── entities.py      # Domain Entities
│   └── repositories.py  # Repository Interfaces (Ports)
│
├── application/         # Application Layer (Use Cases)
│   ├── use_cases.py     # Business Use Cases
│   └── dependencies.py  # Dependency Injection Container
│
├── infrastructure/      # Infrastructure Layer (Adapters)
│   └── repositories.py  # Repository Implementations
│
├── api/                 # Presentation Layer (API)
│   └── routes.py        # FastAPI Routes
│
├── core/                # Core Utilities
│   ├── config.py        # Configuration
│   ├── infra.py         # Infrastructure Setup
│   ├── services.py      # Legacy Services (to be refactored)
│   ├── faiss_adapter.py # FAISS Adapter
│   └── file_storage.py  # File Storage
│
├── ai/                  # AI Services
│   ├── agent.py         # Lesson Agent
│   └── langchain_agent.py # LangChain Agent
│
└── main.py              # Application Entry Point
```

## الطبقات (Layers)

### 1. Domain Layer
**المسؤولية**: يحتوي على الكيانات (Entities) والواجهات (Interfaces) الأساسية

- `entities.py`: كيانات المجال (Session, IndexStatus, SummaryCache)
- `repositories.py`: واجهات المستودعات (Repository Interfaces)

### 2. Application Layer
**المسؤولية**: منطق الأعمال (Business Logic) والاستخدامات (Use Cases)

- `use_cases.py`: حالات الاستخدام:
  - `PDFExtractionUseCase`: استخراج النص من PDF
  - `SummaryUseCase`: توليد الملخصات
  - `LessonAgentUseCase`: وكيل الدروس
  - `ChatAgentUseCase`: وكيل المحادثة
- `dependencies.py`: Dependency Injection Container

### 3. Infrastructure Layer
**المسؤولية**: تنفيذ الواجهات (Implementations)

- `repositories.py`: تنفيذ المستودعات:
  - `InMemorySessionRepository`
  - `InMemoryCacheRepository`
  - `FAISSVectorStoreRepository`
  - `InMemoryIndexStatusRepository`

### 4. Presentation Layer (API)
**المسؤولية**: واجهة المستخدم (API Endpoints)

- `routes.py`: جميع endpoints:
  - `POST /upload`: رفع ملف PDF
  - `GET /summarize-gemini`: توليد ملخص
  - `GET /agent`: وكيل الدروس
  - `GET /chat`: وكيل المحادثة
  - `GET /index-status/{session_id}`: حالة الفهرس
  - `DELETE /session/{session_id}`: حذف جلسة

## Design Patterns المستخدمة

### 1. Repository Pattern
فصل منطق الوصول إلى البيانات عن منطق الأعمال

### 2. Dependency Injection
إدارة التبعيات بشكل مركزي في `dependencies.py`

### 3. Use Case Pattern
كل حالة استخدام في ملف منفصل

### 4. Singleton Pattern
Repositories كـ singletons

## المزايا

1. **قابلية الصيانة**: كل طبقة مستقلة وواضحة
2. **قابلية التوسعة**: إضافة ميزات جديدة سهل
3. **قابلية الاختبار**: كل طبقة قابلة للاختبار بشكل منفصل
4. **فصل الاهتمامات**: كل طبقة لها مسؤولية واحدة
5. **استقلالية**: يمكن تغيير التنفيذ دون التأثير على الطبقات الأخرى

## كيفية إضافة ميزة جديدة

1. **إضافة Entity** في `domain/entities.py`
2. **إضافة Repository Interface** في `domain/repositories.py`
3. **إضافة Repository Implementation** في `infrastructure/repositories.py`
4. **إضافة Use Case** في `application/use_cases.py`
5. **إضافة Dependency** في `application/dependencies.py`
6. **إضافة Route** في `api/routes.py`

## الأكواد المحذوفة

- ✅ `ai/ollama.py` - غير مستخدم
- ✅ `PyPDF2` - تم استبداله بـ `pypdfium2`
- ✅ الكود المعلق في `main.py`

## التحسينات المستقبلية

- [ ] إضافة Unit Tests
- [ ] إضافة Integration Tests
- [ ] استخدام Database بدلاً من In-Memory
- [ ] إضافة Message Queue للمهام الطويلة
- [ ] إضافة Authentication & Authorization
- [ ] إضافة Rate Limiting
- [ ] إضافة Monitoring & Logging

