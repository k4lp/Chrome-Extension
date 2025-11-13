"""Settings dialog for configuring the application."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFormLayout,
    QTimeEdit,
    QGroupBox,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTime
from loguru import logger

from ...config.defaults import AVAILABLE_MODELS, PROMPT_VARIANTS, FONT_FAMILIES


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, config_manager, parent=None):
        """Initialize settings dialog.

        Args:
            config_manager: Configuration manager
            parent: Parent widget
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.settings = config_manager.settings.model_copy(deep=True)

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_gemini_tab(), "Gemini")
        tabs.addTab(self._create_agent_tab(), "Agent Behavior")
        tabs.addTab(self._create_storage_tab(), "Storage")
        tabs.addTab(self._create_automation_tab(), "Automations")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        layout.addRow("Theme:", self.theme_combo)

        # Font
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(FONT_FAMILIES)
        layout.addRow("Font Family:", self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        layout.addRow("Font Size:", self.font_size_spin)

        # Compact mode
        self.compact_mode_check = QCheckBox()
        layout.addRow("Compact Mode:", self.compact_mode_check)

        # Show context panel
        self.show_context_check = QCheckBox()
        layout.addRow("Show Context Panel:", self.show_context_check)

        return widget

    def _create_gemini_tab(self) -> QWidget:
        """Create Gemini settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # API Keys (multiple, newline-delimited)
        from PyQt6.QtWidgets import QPlainTextEdit

        self.api_keys_edit = QPlainTextEdit()
        self.api_keys_edit.setPlaceholderText(
            "Enter your Gemini API key(s)...\n"
            "One per line for automatic rotation on rate limits.\n"
            "Example:\n"
            "AIzaSyAbc123...\n"
            "AIzaSyDef456..."
        )
        self.api_keys_edit.setMaximumHeight(120)
        layout.addRow("API Keys:", self.api_keys_edit)

        help_label = QLabel(
            '<a href="https://makersuite.google.com/app/apikey">Get API Key</a> | '
            'Multiple keys enable automatic rotation on rate limits'
        )
        help_label.setOpenExternalLinks(True)
        layout.addRow("", help_label)

        # Model selection with refresh button
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(AVAILABLE_MODELS)
        self.model_combo.setEditable(True)  # Allow custom model names
        model_layout.addWidget(self.model_combo, stretch=1)

        self.refresh_models_btn = QPushButton("🔄 Refresh")
        self.refresh_models_btn.setMaximumWidth(100)
        self.refresh_models_btn.clicked.connect(self._refresh_models)
        self.refresh_models_btn.setToolTip("Fetch available models from Gemini API")
        model_layout.addWidget(self.refresh_models_btn)

        layout.addRow("Model:", model_layout)

        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        layout.addRow("Temperature:", self.temperature_spin)

        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 65536)
        self.max_tokens_spin.setSingleStep(256)
        layout.addRow("Max Output Tokens:", self.max_tokens_spin)

        # System prompt variant
        self.prompt_variant_combo = QComboBox()
        self.prompt_variant_combo.addItems(PROMPT_VARIANTS)
        layout.addRow("Prompt Variant:", self.prompt_variant_combo)

        return widget

    def _create_agent_tab(self) -> QWidget:
        """Create agent behavior tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Auto-apply actions
        self.auto_actions_check = QCheckBox()
        layout.addRow("Auto-apply Actions:", self.auto_actions_check)

        # Ask before destructive
        self.ask_destructive_check = QCheckBox()
        layout.addRow("Confirm Destructive Changes:", self.ask_destructive_check)

        # Max actions per message
        self.max_actions_spin = QSpinBox()
        self.max_actions_spin.setRange(1, 50)
        layout.addRow("Max Actions per Message:", self.max_actions_spin)

        # Memory threshold
        self.memory_threshold_spin = QSpinBox()
        self.memory_threshold_spin.setRange(1, 5)
        layout.addRow("Memory Importance Threshold:", self.memory_threshold_spin)

        # Context options
        self.include_notes_check = QCheckBox()
        layout.addRow("Include Notes in Context:", self.include_notes_check)

        self.include_tasks_check = QCheckBox()
        layout.addRow("Include Tasks in Context:", self.include_tasks_check)

        self.max_context_spin = QSpinBox()
        self.max_context_spin.setRange(1, 50)
        layout.addRow("Max Context Items:", self.max_context_spin)

        # Code execution
        layout.addRow("", QLabel(""))  # Spacer
        self.enable_code_exec_check = QCheckBox()
        layout.addRow("⚠️ Enable Code Execution:", self.enable_code_exec_check)

        warning_label = QLabel(
            "<small style='color: #cc0000;'><b>WARNING:</b> This allows the agent to execute "
            "Python code with full system access. Only enable if you trust the AI.</small>"
        )
        warning_label.setWordWrap(True)
        layout.addRow("", warning_label)

        return widget

    def _create_storage_tab(self) -> QWidget:
        """Create storage settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Database path
        db_layout = QHBoxLayout()
        self.db_path_edit = QLineEdit()
        db_layout.addWidget(self.db_path_edit)

        browse_db_btn = QPushButton("Browse...")
        browse_db_btn.clicked.connect(self._browse_db_path)
        db_layout.addWidget(browse_db_btn)

        layout.addRow("Database Path:", db_layout)

        # Backup directory
        backup_layout = QHBoxLayout()
        self.backup_dir_edit = QLineEdit()
        backup_layout.addWidget(self.backup_dir_edit)

        browse_backup_btn = QPushButton("Browse...")
        browse_backup_btn.clicked.connect(self._browse_backup_dir)
        backup_layout.addWidget(browse_backup_btn)

        layout.addRow("Backup Directory:", backup_layout)

        # Auto-backup
        self.auto_backup_check = QCheckBox()
        layout.addRow("Auto Backup:", self.auto_backup_check)

        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(1, 168)
        self.backup_interval_spin.setSuffix(" hours")
        layout.addRow("Backup Interval:", self.backup_interval_spin)

        return widget

    def _create_automation_tab(self) -> QWidget:
        """Create automation settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Daily review
        daily_group = QGroupBox("Daily Review")
        daily_layout = QFormLayout(daily_group)

        self.daily_review_check = QCheckBox()
        daily_layout.addRow("Enabled:", self.daily_review_check)

        self.daily_review_time = QTimeEdit()
        self.daily_review_time.setDisplayFormat("HH:mm")
        daily_layout.addRow("Time:", self.daily_review_time)

        layout.addWidget(daily_group)

        # Weekly review
        weekly_group = QGroupBox("Weekly Review")
        weekly_layout = QFormLayout(weekly_group)

        self.weekly_review_check = QCheckBox()
        weekly_layout.addRow("Enabled:", self.weekly_review_check)

        self.weekly_review_day = QComboBox()
        self.weekly_review_day.addItems([
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ])
        weekly_layout.addRow("Day:", self.weekly_review_day)

        self.weekly_review_time = QTimeEdit()
        self.weekly_review_time.setDisplayFormat("HH:mm")
        weekly_layout.addRow("Time:", self.weekly_review_time)

        layout.addWidget(weekly_group)

        # Note resurfacing
        resurface_group = QGroupBox("Note Resurfacing")
        resurface_layout = QFormLayout(resurface_group)

        self.resurface_check = QCheckBox()
        resurface_layout.addRow("Enabled:", self.resurface_check)

        self.resurface_age_spin = QSpinBox()
        self.resurface_age_spin.setRange(1, 365)
        self.resurface_age_spin.setSuffix(" days")
        resurface_layout.addRow("Note Age Threshold:", self.resurface_age_spin)

        self.resurface_count_spin = QSpinBox()
        self.resurface_count_spin.setRange(1, 10)
        resurface_layout.addRow("Notes to Resurface:", self.resurface_count_spin)

        layout.addWidget(resurface_group)
        return widget

    def _load_settings(self):
        """Load settings into UI."""
        # General
        self.theme_combo.setCurrentText(self.settings.ui.theme)
        self.font_family_combo.setCurrentText(self.settings.ui.font_family)
        self.font_size_spin.setValue(self.settings.ui.font_size)
        self.compact_mode_check.setChecked(self.settings.ui.compact_mode)
        self.show_context_check.setChecked(self.settings.ui.show_context_panel)

        # Gemini
        self.api_keys_edit.setPlainText(self.settings.api.gemini_api_key)
        self.model_combo.setCurrentText(self.settings.api.default_model)
        self.temperature_spin.setValue(self.settings.api.temperature)
        self.max_tokens_spin.setValue(self.settings.api.max_output_tokens)
        self.prompt_variant_combo.setCurrentText(self.settings.api.system_prompt_variant)

        # Agent
        self.auto_actions_check.setChecked(self.settings.agent_behavior.auto_structured_actions)
        self.ask_destructive_check.setChecked(self.settings.agent_behavior.ask_before_destructive)
        self.max_actions_spin.setValue(self.settings.agent_behavior.max_actions_per_message)
        self.memory_threshold_spin.setValue(
            self.settings.agent_behavior.memory_update_threshold_importance
        )
        self.include_notes_check.setChecked(self.settings.agent_behavior.include_context_notes)
        self.include_tasks_check.setChecked(self.settings.agent_behavior.include_context_tasks)
        self.max_context_spin.setValue(self.settings.agent_behavior.max_context_items)
        self.enable_code_exec_check.setChecked(self.settings.agent_behavior.enable_code_execution)

        # Storage
        self.db_path_edit.setText(self.settings.storage.db_path)
        self.backup_dir_edit.setText(self.settings.storage.backup_dir)
        self.auto_backup_check.setChecked(self.settings.storage.auto_backup_enabled)
        self.backup_interval_spin.setValue(self.settings.storage.auto_backup_interval_hours)

        # Automations
        self.daily_review_check.setChecked(self.settings.automations.daily_review_enabled)
        time_parts = self.settings.automations.daily_review_time.split(":")
        self.daily_review_time.setTime(QTime(int(time_parts[0]), int(time_parts[1])))

        self.weekly_review_check.setChecked(self.settings.automations.weekly_review_enabled)
        self.weekly_review_day.setCurrentIndex(self.settings.automations.weekly_review_day)
        time_parts = self.settings.automations.weekly_review_time.split(":")
        self.weekly_review_time.setTime(QTime(int(time_parts[0]), int(time_parts[1])))

        self.resurface_check.setChecked(self.settings.automations.resurface_notes_enabled)
        self.resurface_age_spin.setValue(self.settings.automations.resurface_notes_age_days)
        self.resurface_count_spin.setValue(self.settings.automations.resurface_notes_count)

    def _save_settings(self):
        """Save settings from UI."""
        # General
        self.settings.ui.theme = self.theme_combo.currentText()
        self.settings.ui.font_family = self.font_family_combo.currentText()
        self.settings.ui.font_size = self.font_size_spin.value()
        self.settings.ui.compact_mode = self.compact_mode_check.isChecked()
        self.settings.ui.show_context_panel = self.show_context_check.isChecked()

        # Gemini - save all API keys
        self.settings.api.gemini_api_key = self.api_keys_edit.toPlainText()
        self.settings.api.default_model = self.model_combo.currentText()
        self.settings.api.temperature = self.temperature_spin.value()
        self.settings.api.max_output_tokens = self.max_tokens_spin.value()
        self.settings.api.system_prompt_variant = self.prompt_variant_combo.currentText()

        # Agent
        self.settings.agent_behavior.auto_structured_actions = self.auto_actions_check.isChecked()
        self.settings.agent_behavior.ask_before_destructive = (
            self.ask_destructive_check.isChecked()
        )
        self.settings.agent_behavior.max_actions_per_message = self.max_actions_spin.value()
        self.settings.agent_behavior.memory_update_threshold_importance = (
            self.memory_threshold_spin.value()
        )
        self.settings.agent_behavior.include_context_notes = self.include_notes_check.isChecked()
        self.settings.agent_behavior.include_context_tasks = self.include_tasks_check.isChecked()
        self.settings.agent_behavior.max_context_items = self.max_context_spin.value()
        self.settings.agent_behavior.enable_code_execution = (
            self.enable_code_exec_check.isChecked()
        )

        # Storage
        self.settings.storage.db_path = self.db_path_edit.text()
        self.settings.storage.backup_dir = self.backup_dir_edit.text()
        self.settings.storage.auto_backup_enabled = self.auto_backup_check.isChecked()
        self.settings.storage.auto_backup_interval_hours = self.backup_interval_spin.value()

        # Automations
        self.settings.automations.daily_review_enabled = self.daily_review_check.isChecked()
        self.settings.automations.daily_review_time = self.daily_review_time.time().toString(
            "HH:mm"
        )

        self.settings.automations.weekly_review_enabled = self.weekly_review_check.isChecked()
        self.settings.automations.weekly_review_day = self.weekly_review_day.currentIndex()
        self.settings.automations.weekly_review_time = self.weekly_review_time.time().toString(
            "HH:mm"
        )

        self.settings.automations.resurface_notes_enabled = self.resurface_check.isChecked()
        self.settings.automations.resurface_notes_age_days = self.resurface_age_spin.value()
        self.settings.automations.resurface_notes_count = self.resurface_count_spin.value()

        # Save to file
        if self.config_manager.save(self.settings):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")

    def _browse_db_path(self):
        """Browse for database path."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Database File", self.db_path_edit.text(), "Database Files (*.db)"
        )
        if path:
            self.db_path_edit.setText(path)

    def _browse_backup_dir(self):
        """Browse for backup directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if path:
            self.backup_dir_edit.setText(path)

    def _refresh_models(self):
        """Refresh available models from Gemini API."""
        try:
            # Get API keys from the text box
            api_keys_text = self.api_keys_edit.toPlainText().strip()

            if not api_keys_text:
                QMessageBox.warning(
                    self,
                    "No API Key",
                    "Please enter at least one Gemini API key before refreshing models."
                )
                return

            # Parse first API key
            api_keys = [k.strip() for k in api_keys_text.split('\n') if k.strip()]
            first_key = api_keys[0]

            # Disable button and show loading
            self.refresh_models_btn.setEnabled(False)
            self.refresh_models_btn.setText("Loading...")

            # Import here to avoid circular imports
            import google.generativeai as genai

            # Configure with first API key
            genai.configure(api_key=first_key)

            # Fetch available models
            models = []
            for model in genai.list_models():
                # Only include generative models
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    models.append(model_name)

            if models:
                # Remember current selection
                current_model = self.model_combo.currentText()

                # Update combo box
                self.model_combo.clear()
                self.model_combo.addItems(sorted(models))

                # Restore selection if it exists
                index = self.model_combo.findText(current_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)

                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully fetched {len(models)} available models from Gemini API."
                )
                logger.info(f"Refreshed model list: {len(models)} models found")
            else:
                QMessageBox.warning(
                    self,
                    "No Models Found",
                    "No generative models were found. Using default model list."
                )

        except ImportError:
            QMessageBox.critical(
                self,
                "Error",
                "google-generativeai package not installed. Please install it first:\n"
                "pip install google-generativeai"
            )
            logger.error("google-generativeai package not installed")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to fetch models from Gemini API:\n{str(e)}\n\n"
                "Please check your API key and internet connection."
            )
            logger.error(f"Failed to refresh models: {e}")

        finally:
            # Re-enable button
            self.refresh_models_btn.setEnabled(True)
            self.refresh_models_btn.setText("🔄 Refresh")
