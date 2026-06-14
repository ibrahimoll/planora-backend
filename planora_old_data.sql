--
-- PostgreSQL database dump
--

\restrict 92c7N9FOatLx9TmifV4H1fifSPF7iOzsGTYc2ILZdmEShQof4BuSPIlE7DDA4Nv

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.users (user_id, username, email, password_hash, full_name, role, is_active, profile_pic, created_at, is_email_verified) VALUES (2, 'iolleik', 'planora.verify@gmail.com', '$argon2id$v=19$m=65536,t=3,p=4$rx3bHZxrTaVGDTY7nqxoRA$5/03aheTsEtosELJKRS/hQGnODeQtQfBlrCMF1Q7EaA', 'Ibrahim Olleik', 'user', true, 'https://lh3.googleusercontent.com/a/ACg8ocJoArCZIhVodZBSW0gvQk_4u4DzMIRE0urZN2qJxMpNun48cA=s96-c', '2026-05-14 11:46:54.551637+03', true);
INSERT INTO public.users (user_id, username, email, password_hash, full_name, role, is_active, profile_pic, created_at, is_email_verified) VALUES (1, 'admin', 'planora.verify@gmail.com', '$argon2id$v=19$m=65536,t=3,p=4$AoJZug4PzB3sA1Ta41nmWg$xF6Gaebb/d3C8V5OZm9f0t+d/kiJ3ONbUjRZXpl55Jg', 'Planora', 'admin', true, NULL, '2026-05-13 15:09:54.422676+03', true);
INSERT INTO public.users (user_id, username, email, password_hash, full_name, role, is_active, profile_pic, created_at, is_email_verified) VALUES (6, 'Mirage', 'olliekhussien59@gmail.com', '$argon2id$v=19$m=65536,t=3,p=4$IizAMccyKRHIvsmkHdN9TA$miCa0tcE5x06EG2lW3hiBkrNkten0GhkbcaJyYcSXbg', 'Hussien Olliek', 'user', true, 'https://api.dicebear.com/9.x/initials/svg?seed=Hussien%20Olliek', '2026-05-20 17:02:40.39871+03', true);


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.teams (team_id, name, created_by, created_at) VALUES (1, 'Step 7 Test Team 20260513151920', 1, '2026-05-13 15:19:26.665439+03');
INSERT INTO public.teams (team_id, name, created_by, created_at) VALUES (2, 'planora-test', 1, '2026-05-13 17:05:58.47238+03');
INSERT INTO public.teams (team_id, name, created_by, created_at) VALUES (3, 'Planora QA Demo Team', 2, '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.projects (project_id, created_by, team_id, title, description, deadline, status, project_type, created_at, updated_at) VALUES (3, 1, NULL, 'Step 8 Personal Comment Test', 'Testing comments for personal task', '2026-05-20 17:11:24.877749+03', 'in_progress', 'personal', '2026-05-13 17:11:24.882509+03', '2026-05-18 15:08:36.665079+03');
INSERT INTO public.projects (project_id, created_by, team_id, title, description, deadline, status, project_type, created_at, updated_at) VALUES (2, 1, NULL, 'Plamora-test', 'TESTING BACKEND ', '2026-05-13 17:01:45.198+03', 'on_hold', 'personal', '2026-05-13 17:01:59.635941+03', '2026-05-18 15:52:14.530775+03');
INSERT INTO public.projects (project_id, created_by, team_id, title, description, deadline, status, project_type, created_at, updated_at) VALUES (1, 1, 1, 'Step 7 Team Project 20260513151920', 'Testing team project tasks', '2026-06-30 23:59:00+03', 'not_started', 'team', '2026-05-13 15:19:26.736093+03', '2026-05-18 15:52:19.289424+03');
INSERT INTO public.projects (project_id, created_by, team_id, title, description, deadline, status, project_type, created_at, updated_at) VALUES (5, 2, 3, 'QA Team Product Release', 'Team project for Step 34 browser QA.', '2026-06-10 10:50:37.753409+03', 'in_progress', 'team', '2026-05-20 10:50:37.874804+03', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.projects (project_id, created_by, team_id, title, description, deadline, status, project_type, created_at, updated_at) VALUES (4, 2, NULL, 'QA Personal Launch Plan', 'Personal project for Step 34 browser QA.', '2026-06-03 10:50:37.753409+03', 'completed', 'personal', '2026-05-20 10:50:37.874804+03', '2026-05-20 11:02:44.816077+03');


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (2, 2, 1, 1, 'TEST', 'backend-test planora', 'high', 1.00, 1.00, 'todo', '2026-05-15 17:03:40.465+03', NULL, '2026-05-13 17:05:06.824453+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (5, 1, 1, 1, 'string', 'string', 'medium', 0.00, 0.00, 'todo', '2026-05-15 12:58:58.478+03', NULL, '2026-05-15 12:59:03.478594+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (11, 2, 1, 1, 'Define scope and success criteria', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 2.00, NULL, 'todo', '2026-05-17 07:55:21.851566+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (12, 2, 1, 1, 'Analyze requirements and constraints', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 3.00, NULL, 'todo', '2026-05-18 04:29:38.994423+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (13, 2, 1, 1, 'Design the project structure', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 4.00, NULL, 'todo', '2026-05-19 01:03:56.13728+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (14, 2, 1, 1, 'Prepare the implementation plan', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 5.00, NULL, 'todo', '2026-05-19 21:38:13.280138+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (15, 2, 1, 1, 'Implement the core features', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 3.50, NULL, 'todo', '2026-05-20 18:12:30.422995+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (16, 2, 1, 1, 'Review and test the work', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 4.50, NULL, 'todo', '2026-05-21 14:46:47.565852+03', NULL, '2026-05-16 11:21:04.705386+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (17, 2, 1, 1, 'Define scope and success criteria', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 2.00, NULL, 'todo', '2026-05-17 07:55:30.239419+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (18, 2, 1, 1, 'Analyze requirements and constraints', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 3.00, NULL, 'todo', '2026-05-18 04:29:47.382276+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (19, 2, 1, 1, 'Design the project structure', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 4.00, NULL, 'todo', '2026-05-19 01:04:04.525133+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (20, 2, 1, 1, 'Prepare the implementation plan', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 5.00, NULL, 'todo', '2026-05-19 21:38:21.667991+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (21, 2, 1, 1, 'Implement the core features', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 3.50, NULL, 'todo', '2026-05-20 18:12:38.810848+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (22, 2, 1, 1, 'Review and test the work', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 4.50, NULL, 'todo', '2026-05-21 14:46:55.953705+03', NULL, '2026-05-16 11:21:13.088309+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (23, 2, 1, 1, 'Define scope and success criteria', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 2.00, NULL, 'todo', '2026-05-17 07:57:12.184206+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (25, 2, 1, 1, 'Design the project structure', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 4.00, NULL, 'todo', '2026-05-19 01:05:46.46992+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (26, 2, 1, 1, 'Prepare the implementation plan', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 5.00, NULL, 'todo', '2026-05-19 21:40:03.612778+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (27, 2, 1, 1, 'Implement the core features', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 3.50, NULL, 'todo', '2026-05-20 18:14:20.755635+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (28, 2, 1, 1, 'Review and test the work', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'high', 4.50, NULL, 'todo', '2026-05-21 14:48:37.898492+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (34, 2, 1, 1, 'Review and test the work', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'high', 4.50, NULL, 'completed', '2026-05-21 14:48:54.914623+03', '2026-05-18 12:58:26.695532+03', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (29, 2, 1, 1, 'Define scope and success criteria', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'high', 2.00, NULL, 'in_progress', '2026-05-17 07:57:29.200337+03', NULL, '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (30, 2, 1, 1, 'Analyze requirements and constraints', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'medium', 3.00, NULL, 'blocked', '2026-05-18 04:31:46.343194+03', NULL, '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (24, 2, 2, 1, 'Analyze requirements and constraints', 'For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.', 'medium', 3.00, NULL, 'todo', '2026-05-18 04:31:29.327063+03', NULL, '2026-05-16 11:22:55.037267+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (33, 2, 1, 1, 'Implement the core features', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'high', 3.50, NULL, 'in_progress', '2026-05-20 18:14:37.771766+03', NULL, '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (31, 2, 2, 1, 'Design the project structure', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'medium', 4.00, NULL, 'completed', '2026-05-19 01:06:03.486051+03', '2026-05-18 13:06:51.926197+03', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (32, 2, 2, 1, 'Prepare the implementation plan', 'For project ''Plamora-test'', complete this step based on: create mobile app', 'medium', 5.00, NULL, 'in_progress', '2026-05-19 21:40:20.628909+03', NULL, '2026-05-16 11:23:12.055136+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (35, 4, 2, 2, 'QA personal completed task', 'Seeded for Step 34 browser QA.', 'medium', 2.00, 2.50, 'completed', '2026-05-18 10:50:37.753409+03', '2026-05-19 10:50:37.753409+03', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (36, 4, 2, 2, 'QA personal in-progress task', 'Seeded for Step 34 browser QA.', 'high', 3.00, NULL, 'in_progress', '2026-05-23 10:50:37.753409+03', NULL, '2026-05-20 10:50:37.874804+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (37, 4, 2, 2, 'QA personal blocked task', 'Seeded for Step 34 browser QA.', 'high', 4.00, NULL, 'blocked', '2026-05-19 10:50:37.753409+03', NULL, '2026-05-20 10:50:37.874804+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (38, 5, 1, 2, 'QA team completed task', 'Seeded for Step 34 browser QA.', 'medium', 3.00, 3.50, 'completed', '2026-05-17 10:50:37.753409+03', '2026-05-19 10:50:37.753409+03', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (39, 5, 2, 2, 'QA team mobile overview task', 'Seeded for Step 34 browser QA.', 'high', 6.00, NULL, 'in_progress', '2026-05-25 10:50:37.753409+03', NULL, '2026-05-20 10:50:37.874804+03');
INSERT INTO public.tasks (task_id, project_id, assigned_to, created_by, title, description, priority, estimated_hours, actual_hours, status, due_date, completed_at, created_at) VALUES (40, 5, 1, 2, 'QA team blocked integration task', 'Seeded for Step 34 browser QA.', 'high', 5.00, NULL, 'blocked', '2026-05-18 10:50:37.753409+03', NULL, '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: activity_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (1, 2, 11, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Define scope and success criteria', 'Ibrahim Olleik created AI-generated task ''Define scope and success criteria''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (2, 2, 12, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Analyze requirements and constraints', 'Ibrahim Olleik created AI-generated task ''Analyze requirements and constraints''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (3, 2, 13, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Design the project structure', 'Ibrahim Olleik created AI-generated task ''Design the project structure''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (4, 2, 14, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Prepare the implementation plan', 'Ibrahim Olleik created AI-generated task ''Prepare the implementation plan''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (5, 2, 15, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Implement the core features', 'Ibrahim Olleik created AI-generated task ''Implement the core features''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (6, 2, 16, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Review and test the work', 'Ibrahim Olleik created AI-generated task ''Review and test the work''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (7, 2, NULL, 1, 'ai_plan_generated', 'admin', 'Ibrahim Olleik', NULL, 'Ibrahim Olleik generated an AI plan for ''Plamora-test''.', '{"source": "local_rule_based_v1", "plan_id": 6, "created_task_ids": [11, 12, 13, 14, 15, 16], "created_task_count": 6}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (8, 2, 17, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Define scope and success criteria', 'Ibrahim Olleik created AI-generated task ''Define scope and success criteria''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (9, 2, 18, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Analyze requirements and constraints', 'Ibrahim Olleik created AI-generated task ''Analyze requirements and constraints''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (10, 2, 19, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Design the project structure', 'Ibrahim Olleik created AI-generated task ''Design the project structure''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (11, 2, 20, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Prepare the implementation plan', 'Ibrahim Olleik created AI-generated task ''Prepare the implementation plan''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (12, 2, 21, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Implement the core features', 'Ibrahim Olleik created AI-generated task ''Implement the core features''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (13, 2, 22, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Review and test the work', 'Ibrahim Olleik created AI-generated task ''Review and test the work''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (14, 2, NULL, 1, 'ai_plan_generated', 'admin', 'Ibrahim Olleik', NULL, 'Ibrahim Olleik generated an AI plan for ''Plamora-test''.', '{"source": "local_rule_based_v1", "plan_id": 7, "created_task_ids": [17, 18, 19, 20, 21, 22], "created_task_count": 6}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (15, 2, 23, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Define scope and success criteria', 'Ibrahim Olleik created AI-generated task ''Define scope and success criteria''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (16, 2, 24, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Analyze requirements and constraints', 'Ibrahim Olleik created AI-generated task ''Analyze requirements and constraints''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (17, 2, 25, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Design the project structure', 'Ibrahim Olleik created AI-generated task ''Design the project structure''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (18, 2, 26, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Prepare the implementation plan', 'Ibrahim Olleik created AI-generated task ''Prepare the implementation plan''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (19, 2, 27, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Implement the core features', 'Ibrahim Olleik created AI-generated task ''Implement the core features''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (20, 2, 28, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Review and test the work', 'Ibrahim Olleik created AI-generated task ''Review and test the work''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (21, 2, NULL, 1, 'ai_plan_generated', 'admin', 'Ibrahim Olleik', NULL, 'Ibrahim Olleik generated an AI plan for ''Plamora-test''.', '{"source": "local_rule_based_v1", "plan_id": 8, "created_task_ids": [23, 24, 25, 26, 27, 28], "created_task_count": 6}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (22, 2, 29, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Define scope and success criteria', 'Ibrahim Olleik created AI-generated task ''Define scope and success criteria''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (23, 2, 30, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Analyze requirements and constraints', 'Ibrahim Olleik created AI-generated task ''Analyze requirements and constraints''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (24, 2, 31, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Design the project structure', 'Ibrahim Olleik created AI-generated task ''Design the project structure''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (25, 2, 32, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Prepare the implementation plan', 'Ibrahim Olleik created AI-generated task ''Prepare the implementation plan''.', '{"priority": "medium", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (26, 2, 33, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Implement the core features', 'Ibrahim Olleik created AI-generated task ''Implement the core features''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (27, 2, 34, 1, 'task_created', 'admin', 'Ibrahim Olleik', 'Review and test the work', 'Ibrahim Olleik created AI-generated task ''Review and test the work''.', '{"priority": "high", "assigned_to": 1, "generated_by_ai_plan": true}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (28, 2, NULL, 1, 'ai_plan_generated', 'admin', 'Ibrahim Olleik', NULL, 'Ibrahim Olleik generated an AI plan for ''Plamora-test''.', '{"source": "local_rule_based_v1", "plan_id": 9, "created_task_ids": [29, 30, 31, 32, 33, 34], "created_task_count": 6}', '2026-05-16 11:23:12.055136+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (29, 4, NULL, 2, 'project_created', 'iolleik', 'Ibrahim Olleik', NULL, 'Seeded project_created activity for Step 34 browser QA.', '{"seeded_for": "step_34_browser_qa"}', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (30, 4, 35, 2, 'task_completed', 'iolleik', 'Ibrahim Olleik', 'QA personal completed task', 'Seeded task_completed activity for Step 34 browser QA.', '{"seeded_for": "step_34_browser_qa"}', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.activity_logs (activity_id, project_id, task_id, actor_id, event_type, actor_username_snapshot, actor_full_name_snapshot, task_title_snapshot, message, metadata, created_at) VALUES (31, 5, 38, 1, 'task_completed', 'admin', 'Planora', 'QA team completed task', 'Seeded task_completed activity for Step 34 browser QA.', '{"seeded_for": "step_34_browser_qa"}', '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: admin_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (1, 1, 2, 'changed_user_role:user_id=2:old_role=user:new_role=user', '2026-05-18 09:32:38.625009+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (2, 1, 2, 'deactivated_user:user_id=2', '2026-05-18 10:01:26.221248+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (3, 1, 2, 'changed_user_role:user_id=2:old_role=user:new_role=admin', '2026-05-18 10:01:30.446727+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (4, 1, 2, 'changed_user_role:user_id=2:old_role=admin:new_role=user', '2026-05-18 10:01:31.770675+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (5, 1, 2, 'changed_user_role:user_id=2:old_role=user:new_role=admin', '2026-05-18 10:01:32.848631+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (6, 1, 2, 'changed_user_role:user_id=2:old_role=admin:new_role=user', '2026-05-18 10:01:33.461981+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (7, 1, 2, 'activated_user:user_id=2', '2026-05-18 10:02:00.315752+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (8, 1, 2, 'changed_user_role:user_id=2:old_role=user:new_role=admin', '2026-05-18 10:03:23.757198+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (9, 1, 2, 'changed_user_role:user_id=2:old_role=admin:new_role=user', '2026-05-18 10:03:25.019908+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (10, 1, 2, 'deactivated_user:user_id=2', '2026-05-18 10:03:29.569515+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (11, 1, 2, 'activated_user:user_id=2', '2026-05-18 10:03:30.086106+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (12, 1, 1, 'changed_project_status:project_id=1:old_status=not_started:new_status=completed', '2026-05-18 11:21:28.233384+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (13, 1, 1, 'changed_project_status:project_id=2:old_status=not_started:new_status=in_progress', '2026-05-18 11:21:36.563909+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (14, 1, 1, 'changed_project_status:project_id=3:old_status=not_started:new_status=on_hold', '2026-05-18 11:21:46.391227+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (15, 1, 1, 'changed_project_status:project_id=1:old_status=completed:new_status=cancelled', '2026-05-18 11:28:46.244979+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (16, 1, 1, 'changed_project_status:project_id=2:old_status=in_progress:new_status=completed', '2026-05-18 11:28:50.030203+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (17, 1, 1, 'changed_project_status:project_id=3:old_status=on_hold:new_status=completed', '2026-05-18 11:28:54.154853+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (18, 1, 1, 'changed_project_status:project_id=2:old_status=completed:new_status=on_hold', '2026-05-18 12:03:26.731342+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (19, 1, 1, 'changed_task_assignment:task_id=31:old_assigned_to=1:new_assigned_to=1', '2026-05-18 12:58:15.512781+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (20, 1, 1, 'changed_task_assignment:task_id=34:old_assigned_to=1:new_assigned_to=1', '2026-05-18 12:58:23.449565+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (21, 1, 1, 'changed_task_status:task_id=34:old_status=todo:new_status=completed', '2026-05-18 12:58:26.691923+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (22, 1, 1, 'changed_task_status:task_id=29:old_status=todo:new_status=in_progress', '2026-05-18 12:58:29.812088+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (23, 1, 1, 'changed_task_status:task_id=30:old_status=todo:new_status=blocked', '2026-05-18 12:58:32.792682+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (24, 1, 2, 'changed_task_assignment:task_id=24:old_assigned_to=1:new_assigned_to=2', '2026-05-18 13:06:25.59048+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (25, 1, 1, 'changed_task_status:task_id=32:old_status=todo:new_status=blocked', '2026-05-18 13:06:40.872566+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (26, 1, 1, 'changed_task_status:task_id=33:old_status=todo:new_status=in_progress', '2026-05-18 13:06:43.488618+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (27, 1, 1, 'changed_task_assignment:task_id=31:old_assigned_to=1:new_assigned_to=1', '2026-05-18 13:06:47.607021+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (28, 1, 1, 'changed_task_status:task_id=31:old_status=todo:new_status=completed', '2026-05-18 13:06:51.92212+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (29, 1, 2, 'changed_task_assignment:task_id=31:old_assigned_to=1:new_assigned_to=2', '2026-05-18 13:06:53.933596+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (30, 1, 1, 'changed_project_status:project_id=2:old_status=on_hold:new_status=in_progress', '2026-05-18 13:25:58.162201+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (31, 1, 1, 'changed_project_status:project_id=3:old_status=completed:new_status=in_progress', '2026-05-18 15:08:36.665079+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (32, 1, 1, 'changed_project_status:project_id=2:old_status=in_progress:new_status=on_hold', '2026-05-18 15:52:14.530775+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (33, 1, 1, 'changed_project_status:project_id=1:old_status=cancelled:new_status=not_started', '2026-05-18 15:52:19.289424+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (34, 1, 2, 'changed_task_assignment:task_id=32:old_assigned_to=1:new_assigned_to=2', '2026-05-19 15:25:49.189173+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (35, 1, 2, 'changed_task_status:task_id=32:old_status=blocked:new_status=in_progress', '2026-05-19 15:25:51.42035+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (36, 1, 2, 'Seeded Step 34 browser QA data', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (37, 1, 1, 'Reviewed Step 34 browser QA workload', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.admin_logs (log_id, admin_id, target_user_id, action, created_at) VALUES (38, 1, 2, 'changed_project_status:project_id=4:old_status=in_progress:new_status=completed', '2026-05-20 11:02:44.816077+03');


--
-- Data for Name: ai_plans; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.ai_plans (plan_id, project_id, generated_by, input_prompt, generated_plan, created_at) VALUES (6, 2, 1, 'Break this project into clear backend development tasks.', '{"risks": [{"risk": "Deadline pressure", "recommendation": "Start high-priority tasks early and review progress daily."}, {"risk": "Unclear requirements", "recommendation": "Confirm project scope before implementation begins."}], "tasks": [{"title": "Define scope and success criteria", "due_date": "2026-05-17T04:55:21.851566+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 2.0}, {"title": "Analyze requirements and constraints", "due_date": "2026-05-18T01:29:38.994423+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.0}, {"title": "Design the project structure", "due_date": "2026-05-18T22:03:56.137280+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.0}, {"title": "Prepare the implementation plan", "due_date": "2026-05-19T18:38:13.280138+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 5.0}, {"title": "Implement the core features", "due_date": "2026-05-20T15:12:30.422995+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.5}, {"title": "Review and test the work", "due_date": "2026-05-21T11:46:47.565852+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.5}], "source": "local_rule_based_v1", "project": {"title": "Plamora-test", "deadline": "2026-05-13T14:01:45.198000+00:00", "project_id": 2, "project_type": "personal"}, "summary": "Generated a structured plan for ''Plamora-test'' with 6 tasks before the project deadline.", "milestones": [{"name": "Planning completed", "description": "Scope, requirements, and structure are clear."}, {"name": "Implementation completed", "description": "Core project work is finished."}, {"name": "Final review completed", "description": "Testing, cleanup, and final delivery are done."}], "recommendations": ["Review the generated tasks before starting.", "Adjust due dates if the project deadline is very close.", "Assign team tasks manually after generation."], "created_task_ids": [11, 12, 13, 14, 15, 16]}', '2026-05-16 11:21:04.705386+03');
INSERT INTO public.ai_plans (plan_id, project_id, generated_by, input_prompt, generated_plan, created_at) VALUES (7, 2, 1, 'Break this project into clear backend development tasks.', '{"risks": [{"risk": "Deadline pressure", "recommendation": "Start high-priority tasks early and review progress daily."}, {"risk": "Unclear requirements", "recommendation": "Confirm project scope before implementation begins."}], "tasks": [{"title": "Define scope and success criteria", "due_date": "2026-05-17T04:55:30.239419+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 2.0}, {"title": "Analyze requirements and constraints", "due_date": "2026-05-18T01:29:47.382276+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.0}, {"title": "Design the project structure", "due_date": "2026-05-18T22:04:04.525133+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.0}, {"title": "Prepare the implementation plan", "due_date": "2026-05-19T18:38:21.667991+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 5.0}, {"title": "Implement the core features", "due_date": "2026-05-20T15:12:38.810848+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.5}, {"title": "Review and test the work", "due_date": "2026-05-21T11:46:55.953705+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.5}], "source": "local_rule_based_v1", "project": {"title": "Plamora-test", "deadline": "2026-05-13T14:01:45.198000+00:00", "project_id": 2, "project_type": "personal"}, "summary": "Generated a structured plan for ''Plamora-test'' with 6 tasks before the project deadline.", "milestones": [{"name": "Planning completed", "description": "Scope, requirements, and structure are clear."}, {"name": "Implementation completed", "description": "Core project work is finished."}, {"name": "Final review completed", "description": "Testing, cleanup, and final delivery are done."}], "recommendations": ["Review the generated tasks before starting.", "Adjust due dates if the project deadline is very close.", "Assign team tasks manually after generation."], "created_task_ids": [17, 18, 19, 20, 21, 22]}', '2026-05-16 11:21:13.088309+03');
INSERT INTO public.ai_plans (plan_id, project_id, generated_by, input_prompt, generated_plan, created_at) VALUES (8, 2, 1, 'Break this project into clear backend development tasks.', '{"risks": [{"risk": "Deadline pressure", "recommendation": "Start high-priority tasks early and review progress daily."}, {"risk": "Unclear requirements", "recommendation": "Confirm project scope before implementation begins."}], "tasks": [{"title": "Define scope and success criteria", "due_date": "2026-05-17T04:57:12.184206+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 2.0}, {"title": "Analyze requirements and constraints", "due_date": "2026-05-18T01:31:29.327063+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.0}, {"title": "Design the project structure", "due_date": "2026-05-18T22:05:46.469920+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.0}, {"title": "Prepare the implementation plan", "due_date": "2026-05-19T18:40:03.612778+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 5.0}, {"title": "Implement the core features", "due_date": "2026-05-20T15:14:20.755635+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 3.5}, {"title": "Review and test the work", "due_date": "2026-05-21T11:48:37.898492+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: Break this project into clear backend development tasks.", "estimated_hours": 4.5}], "source": "local_rule_based_v1", "project": {"title": "Plamora-test", "deadline": "2026-05-13T14:01:45.198000+00:00", "project_id": 2, "project_type": "personal"}, "summary": "Generated a structured plan for ''Plamora-test'' with 6 tasks before the project deadline.", "milestones": [{"name": "Planning completed", "description": "Scope, requirements, and structure are clear."}, {"name": "Implementation completed", "description": "Core project work is finished."}, {"name": "Final review completed", "description": "Testing, cleanup, and final delivery are done."}], "recommendations": ["Review the generated tasks before starting.", "Adjust due dates if the project deadline is very close.", "Assign team tasks manually after generation."], "created_task_ids": [23, 24, 25, 26, 27, 28]}', '2026-05-16 11:22:55.037267+03');
INSERT INTO public.ai_plans (plan_id, project_id, generated_by, input_prompt, generated_plan, created_at) VALUES (9, 2, 1, 'create mobile app', '{"risks": [{"risk": "Deadline pressure", "recommendation": "Start high-priority tasks early and review progress daily."}, {"risk": "Unclear requirements", "recommendation": "Confirm project scope before implementation begins."}], "tasks": [{"title": "Define scope and success criteria", "due_date": "2026-05-17T04:57:29.200337+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 2.0}, {"title": "Analyze requirements and constraints", "due_date": "2026-05-18T01:31:46.343194+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 3.0}, {"title": "Design the project structure", "due_date": "2026-05-18T22:06:03.486051+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 4.0}, {"title": "Prepare the implementation plan", "due_date": "2026-05-19T18:40:20.628909+00:00", "priority": "medium", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 5.0}, {"title": "Implement the core features", "due_date": "2026-05-20T15:14:37.771766+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 3.5}, {"title": "Review and test the work", "due_date": "2026-05-21T11:48:54.914623+00:00", "priority": "high", "description": "For project ''Plamora-test'', complete this step based on: create mobile app", "estimated_hours": 4.5}], "source": "local_rule_based_v1", "project": {"title": "Plamora-test", "deadline": "2026-05-13T14:01:45.198000+00:00", "project_id": 2, "project_type": "personal"}, "summary": "Generated a structured plan for ''Plamora-test'' with 6 tasks before the project deadline.", "milestones": [{"name": "Planning completed", "description": "Scope, requirements, and structure are clear."}, {"name": "Implementation completed", "description": "Core project work is finished."}, {"name": "Final review completed", "description": "Testing, cleanup, and final delivery are done."}], "recommendations": ["Review the generated tasks before starting.", "Adjust due dates if the project deadline is very close.", "Assign team tasks manually after generation."], "created_task_ids": [29, 30, 31, 32, 33, 34]}', '2026-05-16 11:23:12.055136+03');


--
-- Data for Name: attachments; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.attachments (attachment_id, project_id, task_id, uploaded_by, file_name, file_url, file_type, uploaded_at) VALUES (1, 2, NULL, 1, 'Screenshot 2026-05-13 153440.png', '/uploads/attachments/fd653f65cb3c47ada7cfd6cc4e759d55.png', 'image/png', '2026-05-14 08:53:50.592354+03');


--
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (1, 1, 2, 'Hello', 'user', '2026-05-17 10:08:45.821162+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (2, NULL, 2, 'Hello! I am your Planora project assistant. I checked ''Plamora-test'' and I can help with progress, next tasks, risks, deadlines, and scheduling.', 'ai', '2026-05-17 10:08:45.821162+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (3, 1, 2, 'Hello, How are you doing?', 'user', '2026-05-17 10:09:06.404883+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (4, NULL, 2, 'Hello! I am your Planora project assistant. I checked ''Plamora-test'' and I can help with progress, next tasks, risks, deadlines, and scheduling.', 'ai', '2026-05-17 10:09:06.404883+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (5, 1, 2, 'Hello, How are you doing?', 'user', '2026-05-17 10:11:30.108893+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (6, NULL, 2, 'Hello! I am your Planora project assistant. I checked ''Plamora-test'' and I can help with progress, next tasks, risks, deadlines, and scheduling.', 'ai', '2026-05-17 10:11:30.108893+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (7, 1, 2, 'Hello, How are you doing?', 'user', '2026-05-17 10:11:51.913677+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (8, NULL, 2, 'Hello! I am your Planora project assistant. I checked ''Plamora-test'' and I can help with progress, next tasks, risks, deadlines, and scheduling.', 'ai', '2026-05-17 10:11:51.913677+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (9, 1, 2, 'Hello how are you', 'user', '2026-05-17 10:12:33.192012+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (10, NULL, 2, 'Hello! I am your Planora project assistant. I checked ''Plamora-test'' and I can help with progress, next tasks, risks, deadlines, and scheduling.', 'ai', '2026-05-17 10:12:33.192012+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (11, 1, 2, 'what up', 'user', '2026-05-17 10:14:55.770325+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (12, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:14:55.770325+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (13, 1, 2, 'what up', 'user', '2026-05-17 10:17:33.626341+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (14, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:17:33.626341+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (15, 1, 2, 'Good morning', 'user', '2026-05-17 10:17:52.57279+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (16, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:17:52.57279+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (17, 1, 2, 'Good morning', 'user', '2026-05-17 10:21:28.324505+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (18, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:21:28.324505+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (19, 1, 2, 'good morning', 'user', '2026-05-17 10:22:09.730372+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (20, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:22:09.730372+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (21, 1, 2, 'good morning', 'user', '2026-05-17 10:24:03.985866+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (22, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:24:03.985866+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (23, 1, 2, 'good morning', 'user', '2026-05-17 10:26:01.710217+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (24, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:26:01.710217+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (25, 1, 2, 'good morning', 'user', '2026-05-17 10:26:17.758955+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (26, NULL, 2, 'I checked ''Plamora-test''. Progress is 0.0%, with 0 blocked task(s) and 5 overdue task(s). Recommended next focus:
- TEST | priority: high | status: todo | due: 2026-05-15
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17
- Define scope and success criteria | priority: high | status: todo | due: 2026-05-17', 'ai', '2026-05-17 10:26:17.758955+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (27, 2, 4, 'Deadline', 'user', '2026-05-20 12:41:00.547273+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (28, NULL, 4, '''QA Personal Launch Plan'' deadline is 2026-06-03. You still have 2 incomplete task(s), with around 7.0 estimated hour(s) remaining. Use smart scheduling if due dates need to be reorganized.', 'ai', '2026-05-20 12:41:00.547273+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (29, 2, 4, 'longer the deadline', 'user', '2026-05-20 12:41:13.375012+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (30, NULL, 4, '''QA Personal Launch Plan'' deadline is 2026-06-03. You still have 2 incomplete task(s), with around 7.0 estimated hour(s) remaining. Use smart scheduling if due dates need to be reorganized.', 'ai', '2026-05-20 12:41:13.375012+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (31, 2, 4, 'taks', 'user', '2026-05-20 12:41:19.062536+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (32, NULL, 4, 'I checked ''QA Personal Launch Plan''. Progress is 33.33%, with 1 blocked task(s) and 1 overdue task(s). Recommended next focus:
- QA personal blocked task | priority: high | status: blocked | due: 2026-05-19
- QA personal in-progress task | priority: high | status: in_progress | due: 2026-05-23', 'ai', '2026-05-20 12:41:19.062536+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (33, 2, 4, 'what do i do now', 'user', '2026-05-20 12:41:27.807616+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (34, NULL, 4, 'I checked ''QA Personal Launch Plan''. Progress is 33.33%, with 1 blocked task(s) and 1 overdue task(s). Recommended next focus:
- QA personal blocked task | priority: high | status: blocked | due: 2026-05-19
- QA personal in-progress task | priority: high | status: in_progress | due: 2026-05-23', 'ai', '2026-05-20 12:41:27.807616+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (35, 1, 2, 'How is the weather', 'user', '2026-05-20 13:38:21.037875+03');
INSERT INTO public.chat_messages (message_id, sender_id, project_id, message, sender_type, created_at) VALUES (36, NULL, 2, 'I can only help with the Planora project ''Plamora-test''. Ask me about project progress, tasks, priorities, deadlines, risks, scheduling, team workload, or what to work on next.', 'ai', '2026-05-20 13:38:21.037875+03');


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.comments (comment_id, task_id, user_id, comment_text, created_at) VALUES (1, 2, 1, 'test test', '2026-05-13 17:07:51.673226+03');
INSERT INTO public.comments (comment_id, task_id, user_id, comment_text, created_at) VALUES (2, 2, 1, 'Please check this @iolleik', '2026-05-15 12:57:52.196914+03');
INSERT INTO public.comments (comment_id, task_id, user_id, comment_text, created_at) VALUES (3, 5, 1, 'Please check this @iolleik', '2026-05-15 13:00:34.481008+03');


--
-- Data for Name: comment_mentions; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.comment_mentions (mention_id, comment_id, project_id, task_id, mentioned_user_id, mentioned_by, created_at) VALUES (1, 3, 1, 5, 2, 1, '2026-05-15 13:00:34.481008+03');


--
-- Data for Name: deadline_reminders; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (1, 14, 2, 1, 'due_soon', '2026-05-19 21:38:13.280138+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (2, 20, 2, 1, 'due_soon', '2026-05-19 21:38:21.667991+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (3, 26, 2, 1, 'due_soon', '2026-05-19 21:40:03.612778+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (4, 32, 2, 1, 'due_soon', '2026-05-19 21:40:20.628909+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (5, 24, 2, 2, 'overdue', '2026-05-18 04:31:29.327063+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (6, 30, 2, 1, 'overdue', '2026-05-18 04:31:46.343194+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (7, 29, 2, 1, 'overdue', '2026-05-17 07:57:29.200337+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (8, 25, 2, 1, 'overdue', '2026-05-19 01:05:46.46992+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (9, 23, 2, 1, 'overdue', '2026-05-17 07:57:12.184206+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (10, 19, 2, 1, 'overdue', '2026-05-19 01:04:04.525133+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (11, 18, 2, 1, 'overdue', '2026-05-18 04:29:47.382276+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (12, 17, 2, 1, 'overdue', '2026-05-17 07:55:30.239419+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (13, 13, 2, 1, 'overdue', '2026-05-19 01:03:56.13728+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (14, 12, 2, 1, 'overdue', '2026-05-18 04:29:38.994423+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (15, 11, 2, 1, 'overdue', '2026-05-17 07:55:21.851566+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (16, 2, 2, 1, 'overdue', '2026-05-15 17:03:40.465+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (17, 5, 1, 1, 'overdue', '2026-05-15 12:58:58.478+03', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (18, 32, 2, 2, 'due_soon', '2026-05-19 21:40:20.628909+03', '2026-05-19 15:25:49.339544+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (19, 15, 2, 1, 'due_soon', '2026-05-20 18:12:30.422995+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (20, 21, 2, 1, 'due_soon', '2026-05-20 18:12:38.810848+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (21, 27, 2, 1, 'due_soon', '2026-05-20 18:14:20.755635+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (22, 33, 2, 1, 'due_soon', '2026-05-20 18:14:37.771766+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (23, 32, 2, 2, 'overdue', '2026-05-19 21:40:20.628909+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (24, 26, 2, 1, 'overdue', '2026-05-19 21:40:03.612778+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (25, 20, 2, 1, 'overdue', '2026-05-19 21:38:21.667991+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (26, 14, 2, 1, 'overdue', '2026-05-19 21:38:13.280138+03', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (27, 40, 5, 1, 'overdue', '2026-05-18 10:50:37.753409+03', '2026-05-20 11:02:51.126783+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (28, 37, 4, 2, 'overdue', '2026-05-19 10:50:37.753409+03', '2026-05-20 11:02:51.126783+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (29, 16, 2, 1, 'due_soon', '2026-05-21 14:46:47.565852+03', '2026-05-20 14:51:32.261584+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (30, 22, 2, 1, 'due_soon', '2026-05-21 14:46:55.953705+03', '2026-05-20 14:51:32.261584+03');
INSERT INTO public.deadline_reminders (reminder_id, task_id, project_id, user_id, reminder_type, due_date_snapshot, generated_at) VALUES (31, 28, 2, 1, 'due_soon', '2026-05-21 14:48:37.898492+03', '2026-05-20 14:51:32.261584+03');


--
-- Data for Name: device_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.device_tokens (device_token_id, user_id, token, platform, is_active, last_used_at, created_at) VALUES (1, 1, 'fEZFLcYmykcw7TOEO23VaU:APA91bFjTpT4P5VifB8i2vuO0W8JDtVZ2IxNvkzHBs9n0pypFBblKNc8DsfETqYPM-WMmAXhErwiZoAwcY9FsEfdk1fKpZhaBYLbEATk4Rn2bNj3qgLpfjo', 'web', false, '2026-05-17 13:07:31.199547+03', '2026-05-17 13:07:31.199547+03');
INSERT INTO public.device_tokens (device_token_id, user_id, token, platform, is_active, last_used_at, created_at) VALUES (2, 1, 'cew34NH_RlUHoKqvZSVoXd:APA91bE_4Z8iX_eFULHN8j-lxW-DaNZd4Er7dCl0xndEVzcWPxfqt6GNvmyvXyzQfH9NQEJPzRGzTMVuGYa2BQT_Q6naZe7z6Xr5-h_dVE8klKLw1Gy0ozQ', 'web', false, '2026-05-19 14:06:54.889378+03', '2026-05-19 14:06:54.889378+03');
INSERT INTO public.device_tokens (device_token_id, user_id, token, platform, is_active, last_used_at, created_at) VALUES (3, 1, 'cew34NH_RlUHoKqvZSVoXd:APA91bFRMMShS2bu3ycyUdcrfY42oxvlfqUKdjZSErA4ORVSBsIEDZp-zhqIGMalrci2EBfSnjuCY36wjnK4_QrsXoNr3fUb7bTsZOXe4Jxg6l7FgE-Uum0', 'web', true, '2026-05-19 14:29:01.561747+03', '2026-05-19 14:29:01.561747+03');


--
-- Data for Name: email_verification_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.email_verification_codes (verification_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (1, 1, 'c61b49cc6d1d087da9675c3f718e074e03eff8aa3af68bd8050eedfc7c1f3cbc', '2026-05-13 15:14:54.497955+03', '2026-05-13 15:10:30.702472+03', '2026-05-13 15:09:54.422676+03');
INSERT INTO public.email_verification_codes (verification_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (2, 6, 'c66265ad5c4847e83b1f3f191a06d452c8431dea773e27b77e37f7d2d4f0aa1a', '2026-05-20 17:07:40.486106+03', '2026-05-20 17:03:01.871091+03', '2026-05-20 17:02:40.39871+03');


--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.invitations (invitation_id, invited_by, invited_user_id, email, team_id, project_id, role, status, expires_at, created_at, responded_at) VALUES (4, 1, 2, NULL, 1, NULL, 'member', 'accepted', '2026-05-22 12:02:47.764379+03', '2026-05-15 12:02:47.759038+03', '2026-05-15 12:14:30.241895+03');


--
-- Data for Name: notification_preferences; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.notification_preferences (preference_id, user_id, task_notifications, project_notifications, team_notifications, comment_notifications, mention_notifications, invite_notifications, deadline_notifications, ai_notifications, risk_notifications, system_notifications, push_enabled, email_enabled, updated_at, created_at) VALUES (1, 1, true, true, true, true, true, true, true, true, true, true, true, false, '2026-05-19 09:35:08.631493+03', '2026-05-17 13:07:58.806901+03');


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (1, 1, 'Welcome to Planora', 'Your notification system is working.', true, 'system', '2026-05-15 10:19:57.555982+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (6, 1, 'Team invitation accepted', 'Ibrahim Olleik accepted your team invitation.', true, 'invite', '2026-05-15 12:14:30.226315+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (8, 1, 'Task deadline reminder', 'Task "Prepare the implementation plan" in project "Plamora-test" is due soon: 2026-05-19T21:38:13.280138+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (9, 1, 'Task deadline reminder', 'Task "Prepare the implementation plan" in project "Plamora-test" is due soon: 2026-05-19T21:38:21.667991+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (10, 1, 'Task deadline reminder', 'Task "Prepare the implementation plan" in project "Plamora-test" is due soon: 2026-05-19T21:40:03.612778+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (11, 1, 'Task deadline reminder', 'Task "Prepare the implementation plan" in project "Plamora-test" is due soon: 2026-05-19T21:40:20.628909+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (13, 1, 'Task overdue', 'Task "Analyze requirements and constraints" in project "Plamora-test" is overdue. Deadline was: 2026-05-18T04:31:46.343194+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (14, 1, 'Task overdue', 'Task "Define scope and success criteria" in project "Plamora-test" is overdue. Deadline was: 2026-05-17T07:57:29.200337+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (15, 1, 'Task overdue', 'Task "Design the project structure" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T01:05:46.469920+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (16, 1, 'Task overdue', 'Task "Define scope and success criteria" in project "Plamora-test" is overdue. Deadline was: 2026-05-17T07:57:12.184206+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (17, 1, 'Task overdue', 'Task "Design the project structure" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T01:04:04.525133+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (18, 1, 'Task overdue', 'Task "Analyze requirements and constraints" in project "Plamora-test" is overdue. Deadline was: 2026-05-18T04:29:47.382276+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (19, 1, 'Task overdue', 'Task "Define scope and success criteria" in project "Plamora-test" is overdue. Deadline was: 2026-05-17T07:55:30.239419+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (20, 1, 'Task overdue', 'Task "Design the project structure" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T01:03:56.137280+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (21, 1, 'Task overdue', 'Task "Analyze requirements and constraints" in project "Plamora-test" is overdue. Deadline was: 2026-05-18T04:29:38.994423+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (22, 1, 'Task overdue', 'Task "Define scope and success criteria" in project "Plamora-test" is overdue. Deadline was: 2026-05-17T07:55:21.851566+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (23, 1, 'Task overdue', 'Task "TEST" in project "Plamora-test" is overdue. Deadline was: 2026-05-15T17:03:40.465000+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (24, 1, 'Task overdue', 'Task "string" in project "Step 7 Team Project 20260513151920" is overdue. Deadline was: 2026-05-15T12:58:58.478000+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (26, 1, 'Task deadline reminder', 'Task "Implement the core features" in project "Plamora-test" is due soon: 2026-05-20T18:12:30.422995+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (27, 1, 'Task deadline reminder', 'Task "Implement the core features" in project "Plamora-test" is due soon: 2026-05-20T18:12:38.810848+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (28, 1, 'Task deadline reminder', 'Task "Implement the core features" in project "Plamora-test" is due soon: 2026-05-20T18:14:20.755635+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (29, 1, 'Task deadline reminder', 'Task "Implement the core features" in project "Plamora-test" is due soon: 2026-05-20T18:14:37.771766+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (31, 1, 'Task overdue', 'Task "Prepare the implementation plan" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T21:40:03.612778+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (32, 1, 'Task overdue', 'Task "Prepare the implementation plan" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T21:38:21.667991+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (33, 1, 'Task overdue', 'Task "Prepare the implementation plan" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T21:38:13.280138+03:00.', false, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (35, 1, 'QA high-risk project', 'Seeded notification for Step 34 browser QA.', false, 'risk', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (37, 1, 'Task overdue', 'Task "QA team blocked integration task" in project "QA Team Product Release" is overdue. Deadline was: 2026-05-18T10:50:37.753409+03:00.', false, 'deadline', '2026-05-20 11:02:51.126783+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (5, 2, 'New team invitation', 'Ibrahim Olleik invited you to join Step 7 Test Team 20260513151920.', true, 'invite', '2026-05-15 12:02:47.759038+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (7, 2, 'You were mentioned in a comment', 'Ibrahim Olleik mentioned you on task ''string''.', true, 'mention', '2026-05-15 13:00:34.481008+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (12, 2, 'Task overdue', 'Task "Analyze requirements and constraints" in project "Plamora-test" is overdue. Deadline was: 2026-05-18T04:31:29.327063+03:00.', true, 'deadline', '2026-05-19 15:18:54.600891+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (25, 2, 'Task deadline reminder', 'Task "Prepare the implementation plan" in project "Plamora-test" is due soon: 2026-05-19T21:40:20.628909+03:00.', true, 'deadline', '2026-05-19 15:25:49.339544+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (30, 2, 'Task overdue', 'Task "Prepare the implementation plan" in project "Plamora-test" is overdue. Deadline was: 2026-05-19T21:40:20.628909+03:00.', true, 'deadline', '2026-05-20 08:41:06.855283+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (34, 2, 'QA deadline reminder', 'Seeded notification for Step 34 browser QA.', true, 'deadline', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (36, 2, 'QA task assignment', 'Seeded notification for Step 34 browser QA.', true, 'task', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (38, 2, 'Task overdue', 'Task "QA personal blocked task" in project "QA Personal Launch Plan" is overdue. Deadline was: 2026-05-19T10:50:37.753409+03:00.', true, 'deadline', '2026-05-20 11:02:51.126783+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (39, 1, 'Task deadline reminder', 'Task "Review and test the work" in project "Plamora-test" is due soon: 2026-05-21T14:46:47.565852+03:00.', false, 'deadline', '2026-05-20 14:51:32.261584+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (40, 1, 'Task deadline reminder', 'Task "Review and test the work" in project "Plamora-test" is due soon: 2026-05-21T14:46:55.953705+03:00.', false, 'deadline', '2026-05-20 14:51:32.261584+03');
INSERT INTO public.notifications (notification_id, user_id, title, message, is_read, type, created_at) VALUES (41, 1, 'Task deadline reminder', 'Task "Review and test the work" in project "Plamora-test" is due soon: 2026-05-21T14:48:37.898492+03:00.', false, 'deadline', '2026-05-20 14:51:32.261584+03');


--
-- Data for Name: oauth_accounts; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.oauth_accounts (oauth_account_id, user_id, provider, provider_user_id, provider_email, created_at) VALUES (1, 2, 'google', '108645349434868867222', 'planora.verify@gmail.com', '2026-05-14 11:46:54.551637+03');


--
-- Data for Name: password_reset_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (5, 2, '0909bb7b2f8aa044b759dd0809ed8591e2f4d3e262630257b2c2445e43b42f2e', '2026-05-14 13:14:03.982175+03', '2026-05-14 13:18:04.083324+03', '2026-05-14 13:12:03.974601+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (6, 2, '4e0bee124071171e00cdc7c4dd62b493e172ae203de4b8e137d9af7b42bf173b', '2026-05-14 13:20:04.083375+03', '2026-05-14 13:26:46.198575+03', '2026-05-14 13:18:04.074192+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (8, 2, '98505259f0e888ef3a520ad8e8106cc88547695c1e9b4f39dce137c6df84e882', '2026-05-14 13:28:46.198666+03', '2026-05-14 13:28:17.566608+03', '2026-05-14 13:26:46.179611+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (9, 2, '186f87d0830f49ca011bb65557d7125990d19b2c0244e82b36a825d0b21319b7', '2026-05-15 12:14:41.991387+03', '2026-05-15 12:13:26.425258+03', '2026-05-15 12:12:41.98454+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (7, 1, '75ec5c2ca25ca096c99eb8fecae11eace28e7a4063800e86d514bda4eb7c9299', '2026-05-14 13:21:52.701028+03', '2026-05-18 08:04:15.2115+03', '2026-05-14 13:19:52.699369+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (10, 1, 'f846934ea992d9083db0f71a7f249c76510f54e6bcff68b9742310441dc18cdf', '2026-05-18 08:06:15.211694+03', NULL, '2026-05-18 08:04:15.17641+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (11, 2, '3f266f816b6aa7879efb9bba93580ec62746b4f59301c09b86562d8049d4613b', '2026-05-18 08:23:50.033904+03', '2026-05-18 18:55:56.546094+03', '2026-05-18 08:21:50.029558+03');
INSERT INTO public.password_reset_codes (reset_code_id, user_id, code_hash, expires_at, used_at, created_at) VALUES (12, 2, 'a0870e6802e3a061e21680c22768f4ea025d034bdcaf622bbf64240b131aca06', '2026-05-18 18:57:56.553284+03', NULL, '2026-05-18 18:55:56.531911+03');


--
-- Data for Name: project_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_members (member_id, project_id, user_id, role, joined_at) VALUES (1, 1, 1, 'owner', '2026-05-13 15:19:26.736093+03');
INSERT INTO public.project_members (member_id, project_id, user_id, role, joined_at) VALUES (2, 1, 2, 'member', '2026-05-15 12:14:30.226315+03');
INSERT INTO public.project_members (member_id, project_id, user_id, role, joined_at) VALUES (3, 5, 2, 'owner', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.project_members (member_id, project_id, user_id, role, joined_at) VALUES (4, 5, 1, 'manager', '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: report_exports; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (1, 3, 1, 'project', 'json', 'Step 8 Personal Comment Test', 'in_progress', 'personal', 0, 0.00, 'admin', 'Planora', '{"overdue_tasks": 0, "pending_tasks": 0, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 10:23:36.983336+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (2, 3, 1, 'project', 'json', 'Step 8 Personal Comment Test', 'in_progress', 'personal', 0, 0.00, 'admin', 'Planora', '{"overdue_tasks": 0, "pending_tasks": 0, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 10:39:56.931362+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (3, 4, 2, 'project', 'json', 'QA Personal Launch Plan', 'in_progress', 'personal', 3, 33.33, 'iolleik', 'Ibrahim Olleik', '{"seeded_for": "step_34_browser_qa"}', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (4, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"seeded_for": "step_34_browser_qa"}', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (5, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 10:56:10.078859+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (6, 3, 1, 'project', 'json', 'Step 8 Personal Comment Test', 'in_progress', 'personal', 0, 0.00, 'admin', 'Planora', '{"overdue_tasks": 0, "pending_tasks": 0, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 10:56:12.856366+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (7, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 10:56:14.055534+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (8, 1, 1, 'project', 'json', 'Step 7 Team Project 20260513151920', 'not_started', 'team', 1, 0.00, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 1, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 10:56:18.242082+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (9, 3, 1, 'project', 'json', 'Step 8 Personal Comment Test', 'in_progress', 'personal', 0, 0.00, 'admin', 'Planora', '{"overdue_tasks": 0, "pending_tasks": 0, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 11:02:29.610193+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (10, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 11:02:30.968163+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (11, 3, 1, 'project', 'json', 'Step 8 Personal Comment Test', 'in_progress', 'personal', 0, 0.00, 'admin', 'Planora', '{"overdue_tasks": 0, "pending_tasks": 0, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 11:02:32.247568+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (12, 1, 1, 'project', 'json', 'Step 7 Team Project 20260513151920', 'not_started', 'team', 1, 0.00, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 1, "completed_tasks": 0, "actual_hours_total": 0.0, "estimated_hours_total": 0.0}', '2026-05-20 11:02:33.256122+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (13, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 11:02:48.372898+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (14, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 11:04:25.410647+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (15, 5, 1, 'project', 'json', 'QA Team Product Release', 'in_progress', 'team', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 3.5, "estimated_hours_total": 14.0}', '2026-05-20 11:06:06.039624+03');
INSERT INTO public.report_exports (report_export_id, project_id, exported_by, report_type, export_format, project_title_snapshot, project_status_snapshot, project_type_snapshot, task_count_snapshot, completion_percentage_snapshot, exported_by_username_snapshot, exported_by_full_name_snapshot, metadata, created_at) VALUES (16, 4, 1, 'project', 'json', 'QA Personal Launch Plan', 'completed', 'personal', 3, 33.33, 'admin', 'Planora', '{"overdue_tasks": 1, "pending_tasks": 2, "completed_tasks": 1, "actual_hours_total": 2.5, "estimated_hours_total": 9.0}', '2026-05-20 11:06:07.764223+03');


--
-- Data for Name: risk_analysis; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.risk_analysis (risk_id, project_id, risk_level, predicted_delay_days, reason, recommendation, created_at) VALUES (1, 4, 'medium', 2, 'Seeded risk data for browser QA.', 'Review blocked or overdue tasks before the demo.', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.risk_analysis (risk_id, project_id, risk_level, predicted_delay_days, reason, recommendation, created_at) VALUES (2, 5, 'high', 5, 'Seeded risk data for browser QA.', 'Review blocked or overdue tasks before the demo.', '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: smart_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: team_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.team_members (team_member_id, team_id, user_id, role, joined_at) VALUES (1, 1, 1, 'owner', '2026-05-13 15:19:26.665439+03');
INSERT INTO public.team_members (team_member_id, team_id, user_id, role, joined_at) VALUES (2, 2, 1, 'owner', '2026-05-13 17:05:58.47238+03');
INSERT INTO public.team_members (team_member_id, team_id, user_id, role, joined_at) VALUES (3, 1, 2, 'admin', '2026-05-15 12:14:30.226315+03');
INSERT INTO public.team_members (team_member_id, team_id, user_id, role, joined_at) VALUES (4, 3, 2, 'owner', '2026-05-20 10:50:37.874804+03');
INSERT INTO public.team_members (team_member_id, team_id, user_id, role, joined_at) VALUES (5, 3, 1, 'admin', '2026-05-20 10:50:37.874804+03');


--
-- Data for Name: user_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.user_progress (progress_id, user_id, project_id, tasks_completed, tasks_total, completion_percentage, updated_at, created_at) VALUES (1, 1, 2, 0, 25, 0.00, '2026-05-16 11:32:16.85232+03', '2026-05-16 11:32:16.85232+03');


--
-- Name: activity_logs_activity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.activity_logs_activity_id_seq', 31, true);


--
-- Name: admin_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admin_logs_log_id_seq', 38, true);


--
-- Name: ai_plans_plan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ai_plans_plan_id_seq', 9, true);


--
-- Name: attachments_attachment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attachments_attachment_id_seq', 1, true);


--
-- Name: chat_messages_message_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_messages_message_id_seq', 36, true);


--
-- Name: comment_mentions_mention_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.comment_mentions_mention_id_seq', 1, true);


--
-- Name: comments_comment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.comments_comment_id_seq', 3, true);


--
-- Name: deadline_reminders_reminder_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.deadline_reminders_reminder_id_seq', 31, true);


--
-- Name: device_tokens_device_token_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.device_tokens_device_token_id_seq', 3, true);


--
-- Name: email_verification_codes_verification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.email_verification_codes_verification_id_seq', 2, true);


--
-- Name: invitations_invitation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.invitations_invitation_id_seq', 4, true);


--
-- Name: notification_preferences_preference_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notification_preferences_preference_id_seq', 1, true);


--
-- Name: notifications_notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notifications_notification_id_seq', 41, true);


--
-- Name: oauth_accounts_oauth_accout_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.oauth_accounts_oauth_accout_id_seq', 1, true);


--
-- Name: password_reset_codes_reset_code_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.password_reset_codes_reset_code_id_seq', 12, true);


--
-- Name: project_members_project_member_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_members_project_member_id_seq', 4, true);


--
-- Name: projects_project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.projects_project_id_seq', 5, true);


--
-- Name: report_exports_report_export_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.report_exports_report_export_id_seq', 16, true);


--
-- Name: risk_analysis_risk_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.risk_analysis_risk_id_seq', 2, true);


--
-- Name: smart_schedules_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.smart_schedules_schedule_id_seq', 1, false);


--
-- Name: tasks_task_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tasks_task_id_seq', 40, true);


--
-- Name: team_members_team_member_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.team_members_team_member_id_seq', 5, true);


--
-- Name: teams_team_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teams_team_id_seq', 3, true);


--
-- Name: user_progress_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_progress_progress_id_seq', 1, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 6, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 92c7N9FOatLx9TmifV4H1fifSPF7iOzsGTYc2ILZdmEShQof4BuSPIlE7DDA4Nv

