# Import/export guide for ContentPages with linked WhatsAppTemplates

## Overview

This guide explains how to import and export ContentPages and WhatsAppTemplates using CSV or Excel files.

**When does this apply?** This guide is relevant when you have ContentPages with linked WhatsAppTemplates attached to them. This typically occurs in:
- Older systems built before the move to standalone templates
- OrderedContentSets that need to contain templates

If you're working with standalone WhatsAppTemplates only (not linked to ContentPages), you can import them independently without following the order requirements below.

## Quick Reference

### Import Order (CRITICAL - only when ContentPages reference templates)
1. **WhatsAppTemplates FIRST**
2. **ContentPages SECOND**

**Why?** ContentPages can reference WhatsAppTemplates via the `whatsapp_template_slug` field. If the template doesn't exist when you import pages that reference it, the import will fail.

### File Formats Supported
- CSV (`.csv`)
- Excel (`.xlsx`)

---

## WhatsAppTemplates

### What Are WhatsAppTemplates?

WhatsAppTemplates are pre-approved message templates that you submit to Meta's WhatsApp Business API. They're used for business-initiated conversations like marketing messages and appointment reminders.

### All Template Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `slug` | Yes | Unique identifier for the template | `appointment-reminder` |
| `category` | Yes | Type of template: MARKETING or UTILITY | `MARKETING` |
| `locale` | Yes | Language code | `en` |
| `message` | Yes | The template message text (use {{1}}, {{2}} for variables) | `Hi {{1}}, your appointment is on {{2}}` |
| `buttons` | No | Interactive buttons (formatted as JSON) | `[{"type": "next_message", "title": "Confirm"}]` |
| `example_values` | No | Example values for variables (comma-separated) | `John,Monday` |
| `image` | No | Image for the template | |
| `submission_name` | No | Name used when submitting to Meta | |
| `submission_status` | No | Approval status from Meta | |
| `submission_result` | No | Result of Meta submission | |

### Template CSV Example

```csv
slug,category,buttons,locale,image,message,example_values,submission_name,submission_status,submission_result
appointment-reminder,MARKETING,"[{""type"": ""next_message"", ""title"": ""Confirm"", ""slug"": """"}]",en,,Hi {{1}}! Your appointment is on {{2}}.,John Smith,Monday,,,
promo-offer,MARKETING,[],en,,Special offer: {{1}}% off!,20,,,
```

### Importing Templates

**Via Admin UI:**
1. Navigate to `/admin/import_whatsapptemplate/`
2. Upload CSV/Excel file
3. Select purge option (delete existing templates)
4. Select locale filter (optional)
5. Click Import

**Import Parameters:**
- **Purge**: `True` deletes ALL existing templates before import. Use cautiously.
- **Locale**: Filter to specific locale (e.g., `en`). Leave empty for all locales.

### Exporting Templates

**Via Admin UI:**
1. Go to WhatsAppTemplates list
2. Select templates to export
3. Choose "Export as CSV" or "Export as XLSX" from action dropdown
4. Click Go

---

## ContentPages

### What Are ContentPages?

ContentPages are individual pieces of content (messages, menus, articles) organized in a tree structure. They support multiple channels: WhatsApp, Web, SMS, USSD, Messenger, and Viber.

### All ContentPage Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `structure` | No | Position in the content tree | `Sub 1.2` |
| `message` | No | Whether this page has a message (0=no, 1=yes) | `1` |
| `page_id` | No | Internal page ID | `101` |
| `slug` | Yes | Unique identifier for the page | `pregnancy-week-1` |
| `parent` | No | Parent page title (for organizing in tree) | `Pregnancy Journey` |
| `web_title` | No | Title for web display | `Week 1: First Steps` |
| `web_subtitle` | No | Subtitle for web display | `Your pregnancy begins` |
| `web_body` | No | Content for web channel | `Welcome to week 1!` |
| `whatsapp_title` | No | Title for WhatsApp | `Week 1` |
| `whatsapp_body` | No | Message text for WhatsApp | `Welcome to week 1!` |
| `whatsapp_template_slug` | No | Reference to a WhatsAppTemplate | `appointment-reminder` |
| `variation_title` | No | Title for message variations | |
| `variation_body` | No | Body for message variations | |
| `list_title` | No | Title for list messages | |
| `list_items` | No | Items in list messages (JSON format) | |
| `sms_title` | No | Title for SMS channel | |
| `sms_body` | No | Message text for SMS | |
| `ussd_title` | No | Title for USSD channel | |
| `ussd_body` | No | Message text for USSD | |
| `messenger_title` | No | Title for Facebook Messenger | |
| `messenger_body` | No | Message text for Messenger | |
| `viber_title` | No | Title for Viber | |
| `viber_body` | No | Message text for Viber | |
| `translation_tag` | No | Tag for translation management | |
| `tags` | No | Categories/tags (comma-separated) | `pregnancy,health` |
| `quick_replies` | No | Quick reply buttons (JSON format) | `[{"type": "next_message", "title": "Next"}]` |
| `triggers` | No | Custom triggers (JSON format) | |
| `buttons` | No | Interactive buttons (JSON format) | |
| `image_link` | No | Image for the page | |
| `doc_link` | No | Document attachment | |
| `media_link` | No | Media file (audio/video) | |
| `related_pages` | No | Related pages (comma-separated slugs) | `week-2,week-3` |
| `footer` | No | Footer text for messages | |
| `language_code` | Yes | Language code (or use `locale`) | `en` |

### ContentPage CSV Example

```csv
structure,message,page_id,slug,parent,web_title,web_subtitle,web_body,whatsapp_title,whatsapp_body,whatsapp_template_slug,locale,tags,quick_replies
Menu 1,0,100,main-menu,,Main Menu,,,,,en,,
Sub 1.1,1,101,pregnancy-info,Main Menu,Pregnancy Info,,,Pregnancy Info,Get helpful info about your pregnancy journey.,,en,pregnancy,"[{""type"": ""next_message"", ""title"": ""Next""}]"
Sub 1.2,1,102,appointment,Main Menu,Appointments,,,Appointment,,appointment-reminder,en,appointments,
```

### Importing ContentPages

**Via Admin UI:**
1. Navigate to `/admin/import/`
2. Upload CSV/Excel file
3. Select purge option
4. Select locale filter (optional)
5. Click Import

**Import Parameters:**
- **Purge**: `True` deletes ALL existing pages before import. **Warning**: This removes entire content tree.
- **Locale**: Filter to specific locale

### Exporting ContentPages

**Via Admin UI:**
1. Go to Pages list in admin
2. Select pages to export
3. Choose "Export as CSV" or "Export as XLSX"
4. Click Go

---

## Relationship: ContentPages ↔ WhatsAppTemplates

### When Templates Are Linked to Pages

In older systems or when using OrderedContentSets, ContentPages can reference WhatsAppTemplates via the `whatsapp_template_slug` field:

```csv
slug,parent,whatsapp_template_slug
appointment-page,Main Menu,appointment-reminder
```

This page will use the `appointment-reminder` template instead of inline `whatsapp_body` text.

### Important Rules (when linking templates to pages)

1. **Choose One**: A page uses EITHER `whatsapp_template_slug` OR `whatsapp_body`, never both
2. **Template Must Exist First**: If you reference a template via `whatsapp_template_slug`, it must already be imported
3. **Same Language**: The template and page must use the same locale (e.g., both `en`)
4. **First Message Only**: You can only use a template for the first message on a page

**Note**: Some implementations use standalone templates that are not linked to ContentPages. In those cases, you can import templates independently without these constraints.

### Example Workflow

**Scenario**: Import content with appointment reminders using WhatsApp template

**Step 1: Export/Create Template CSV** (`templates.csv`)
```csv
slug,category,locale,message,buttons
appointment-reminder,MARKETING,en,Hi {{1}}! Your appointment is {{2}}.,[]
```

**Step 2: Export/Create ContentPages CSV** (`content.csv`)
```csv
slug,parent,whatsapp_title,whatsapp_template_slug,locale
appointments,Main Menu,Appointments,appointment-reminder,en
```

**Step 3: Import in Order**
1. Import `templates.csv` first
2. Import `content.csv` second

**What Happens**: ContentPage with slug `appointments` will use `appointment-reminder` template for WhatsApp messages.

---

## Complete Import/Export Workflows

### Scenario 1: Fresh Import (New System)

**Goal**: Import all content into empty system

**Steps**:
1. Enable purge mode for both imports
2. Import WhatsAppTemplates CSV (purge=True)
3. Import ContentPages CSV (purge=True)

### Scenario 2: Update Existing Content

**Goal**: Update existing pages/templates without deleting

**Steps**:
1. Export current templates/pages
2. Edit the CSV files
3. Import WhatsAppTemplates CSV (purge=False)
4. Import ContentPages CSV (purge=False)

**Note**: Existing content with matching slug and locale will be updated. New content will be added.

### Scenario 3: Add New Locale

**Goal**: Import Spanish content alongside existing English

**Steps**:
1. Create Spanish versions of your template and content CSV files
2. Change the `locale` column to `es` in both files
3. Import templates with locale filter set to `es`, purge=False
4. Import content with locale filter set to `es`, purge=False

**Note**: Your English content will not be changed.

### Scenario 4: Export for Translation

**Goal**: Export English content, translate to French, import French

**Steps**:
1. Export English templates
2. Export English pages
3. Copy the files and translate the text, change locale column to `fr`
4. In the admin, create French locale (Settings > Locales)
5. Create French HomePage using the translate function
6. Import French templates with locale=`fr`
7. Import French pages with locale=`fr`

---

## Common Issues & Troubleshooting

### Error: "Template 'X' does not exist for locale 'Y'"

**Cause**: ContentPage references template that doesn't exist

**Solution**:
1. Verify template slug matches exactly (case-sensitive)
2. Verify template locale matches page locale
3. Import templates before pages
4. Check template successfully imported (no errors)

### Error: "Slug 'X' already exists"

**Cause**: Duplicate slug in same locale

**Solution**:
1. Slugs must be unique within locale
2. Use purge mode to clear existing content
3. Or rename duplicate slugs

### Import Hangs/Takes Long Time

**Cause**: Large import with many pages/templates

**Solution**:
1. Import runs in background thread
2. Check progress bar in admin UI
3. Check system logs for errors
4. Consider splitting large files into smaller batches

### Template Buttons Not Working

**Cause**: Buttons field is not formatted correctly

**Solution**:
1. Buttons must follow the JSON format
2. In CSV files, double-up the quote marks: `"[{""type"": ""next_message""}]"`
3. Ask your technical team if you need help with the button format

### Pages Not Appearing in Tree

**Cause**: Parent page reference incorrect

**Solution**:
1. `parent` field references parent page **title**, not slug
2. Verify parent page exists
3. Check spelling/case of parent title
4. Use `structure` field to indicate tree position (Menu 1, Sub 1.2, etc.)

---

## Best Practices

### 1. Always Backup Before Purge
Export existing content before using purge mode. Purge is permanent and cannot be undone.

### 2. Import Order Checklist
- [ ] WhatsAppTemplates imported
- [ ] Verify templates appear in admin
- [ ] ContentPages imported
- [ ] Verify pages appear in admin
- [ ] Test that template references work

### 3. Locale Management
- Create the locale in Settings > Locales before importing translated content
- Create the HomePage for that locale using the translate function
- Use the locale filter when importing to keep languages separate
- Keep locale codes consistent (always use `en`, not `en-US` or `ENG`)

### 4. Slug Naming Convention
- Use lowercase letters
- Separate words with hyphens: `appointment-reminder`
- Keep slugs short but descriptive
- Don't change slugs after pages are published (this breaks links)

---

## Getting Help

If you run into issues with import/export:
1. Check the error message shown in the admin interface
2. Try with a small sample file first to test
3. Verify the CSV columns match the field names exactly
4. Contact your technical team with the error details
