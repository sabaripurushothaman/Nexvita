# NexVita — Intelligent Healthcare Management Platform

NexVita is a modern, full-stack healthcare management platform designed to bring essential personal healthcare tools into a single, accessible system.

The platform enables users to securely manage health records, monitor personal health information, receive AI-powered assistance for health-related queries, discover nearby healthcare facilities, manage reminders, and access emergency assistance features.

> **NexVita aims to make personal healthcare management more organized, accessible, and technology-driven.**

---

## 🌐 Live Application

**Live Website:**  
https://YOUR-RENDER-URL.onrender.com

> Replace the URL above with your actual Render deployment URL.

---

## ✨ Key Features

### 🔐 Authentication & User Management
- Secure user registration and login
- Password hashing and authentication
- Session-based user management
- User profile management
- Role-based access support

### 🩺 Personal Health Records
- Add and manage personal health records
- Track different types of medical conditions and health information
- Record measurements, values, units, dates, and notes
- View historical health information
- Update and manage existing records

### 🤖 AI Healthcare Assistant
- AI-powered healthcare question answering
- Helps users understand general health-related concepts
- Provides educational information about symptoms, conditions, and wellness
- Designed to provide understandable responses to health-related queries

> **Medical Disclaimer:** NexVita's AI Assistant is intended for informational and educational purposes only. It does not replace a qualified healthcare professional, medical diagnosis, or emergency medical care.

### 🏥 Hospital Discovery
- Find nearby hospitals and healthcare facilities
- Location-based hospital search
- Hospital information including:
  - Name
  - Address
  - Contact information
  - Distance
  - Availability information where provided
  - Map/location links
- Location-based results using external location services

### 🚨 Emergency Assistance
- Dedicated emergency assistance interface
- Quick access to emergency calling
- Location sharing support
- Nearby hospital discovery
- Emergency-contact management
- Emergency workflow designed for quick access during urgent situations

> Emergency features should not be considered a replacement for official emergency services.

### ⏰ Health Reminders
- Create health-related reminders
- Track active reminders
- Manage reminder schedules
- Support for medication and health-management routines

### 📊 Health Dashboard
- Centralized overview of personal health information
- Quick access to health records
- Reminder overview
- Emergency tools
- AI Assistant access
- Healthcare facility discovery

---

## 🏗️ System Architecture

NexVita follows a modular Flask application architecture.

```text
                        ┌─────────────────────┐
                        │      User / Web     │
                        │      Browser        │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Flask Web App     │
                        │      app.py         │
                        └──────────┬──────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
             ▼                     ▼                     ▼
       ┌───────────┐        ┌─────────────┐       ┌─────────────┐
       │  Routes   │        │  Services   │       │   Models    │
       └─────┬─────┘        └──────┬──────┘       └──────┬──────┘
             │                     │                     │
             │              ┌──────┼──────┐              │
             │              │      │      │              │
             ▼              ▼      ▼      ▼              ▼
       Authentication     AI    Hospital  SOS       PostgreSQL
       Dashboard         APIs   Services Services    Database
       Health Records
       Reminders