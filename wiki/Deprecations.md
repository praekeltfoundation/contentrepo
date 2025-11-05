## Deprecations

This section provides information on deprecated features in ContentRepo, including the release in which they were deprecated and when they were removed.

---

### **`next_prompt` Field**

The `next_prompt` field was used to define the button text for navigating to the next message in a sequence. This has been replaced by the more flexible `buttons` field, which supports multiple button types.

* **Deprecated in**: `1.1.0`
* **Removed in**: Currently deprecated and will be removed in a future release.

---

### **`quick_replies` Field**

The `quick_replies` field was used to define button text for templates. This functionality has been consolidated into the `buttons` field for a more unified approach to button management.

* **Deprecated in**: Unreleased
* **Removed in**: Currently deprecated and will be removed in a future release.

---

### **"Age" Question Type**

The "Age" question type in Forms/Assessments was designed for capturing a user's age in years. This has been deprecated in favour of the more versatile "Integer" question type, which allows for a wider range of numerical inputs and validations.

* **Deprecated in**: Unreleased
* **Removed in**: Currently deprecated and will be removed in a future release.

---

### **Content Page-based WhatsApp Templates**

Previously, WhatsApp templates were created directly within a `ContentPage`. This has been updated to a more robust system where templates are managed as standalone entities, allowing for better organization and reuse, and rather linked inside of Content Pages.

* **Deprecated in**: Unreleased
* **Removed in**: Currently deprecated and will be removed in a future release.