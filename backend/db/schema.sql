CREATE TABLE IF NOT EXISTS companies (
    company_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(120) NOT NULL UNIQUE,
    industry VARCHAR(80),
    city VARCHAR(80),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT NOT NULL,
    title VARCHAR(120) NOT NULL,
    city VARCHAR(80),
    job_type VARCHAR(80),
    source_url VARCHAR(500) UNIQUE,
    requirement_json TEXT,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    skill_name VARCHAR(120) NOT NULL UNIQUE,
    category VARCHAR(80),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id BIGINT NOT NULL,
    skill_id BIGINT NOT NULL,
    importance VARCHAR(20) NOT NULL DEFAULT 'medium',
    PRIMARY KEY (job_id, skill_id),
    CONSTRAINT fk_job_skills_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_job_skills_skill
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS crawl_tasks (
    task_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    seed_url VARCHAR(500) NOT NULL,
    source_site VARCHAR(120),
    status VARCHAR(30) NOT NULL DEFAULT 'running',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_crawl_tasks_status_created_at (status, created_at)
);

CREATE TABLE IF NOT EXISTS crawl_records (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    job_id BIGINT,
    source_url VARCHAR(500) NOT NULL,
    title VARCHAR(120),
    raw_text MEDIUMTEXT,
    parsed_json TEXT,
    status VARCHAR(30) NOT NULL,
    error_message TEXT,
    crawled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_crawl_records_task
        FOREIGN KEY (task_id) REFERENCES crawl_tasks(task_id) ON DELETE CASCADE,
    CONSTRAINT fk_crawl_records_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE SET NULL,
    INDEX idx_crawl_records_task_id (task_id),
    INDEX idx_crawl_records_status_crawled_at (status, crawled_at)
);

CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    display_name VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_app_users_role (role)
);


CREATE TABLE IF NOT EXISTS tool_call_logs (
    call_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(80),
    tool_name VARCHAR(120) NOT NULL,
    input_json TEXT,
    output_json TEXT,
    status VARCHAR(30) NOT NULL,
    error_message TEXT,
    latency_ms BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS agent_traces (
    trace_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(80),
    task TEXT NOT NULL,
    skill_name VARCHAR(120),
    trace_json TEXT NOT NULL,
    final_answer TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(80) PRIMARY KEY,
    owner_user_id BIGINT,
    name VARCHAR(120),
    education VARCHAR(200),
    target_roles TEXT,
    target_cities TEXT,
    preferred_work_type VARCHAR(80),
    skills_json TEXT,
    projects_json TEXT,
    weaknesses_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_profiles_owner
        FOREIGN KEY (owner_user_id) REFERENCES app_users(user_id) ON DELETE SET NULL,
    INDEX idx_user_profiles_owner_user_id (owner_user_id)
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(80) NOT NULL,
    job_id BIGINT NOT NULL,
    difficulty VARCHAR(30) NOT NULL DEFAULT 'medium',
    questions_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interview_sessions_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answer_evaluations (
    evaluation_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    score INT NOT NULL,
    dimension_scores_json TEXT NOT NULL,
    strengths_json TEXT NOT NULL,
    weaknesses_json TEXT NOT NULL,
    improved_answer TEXT NOT NULL,
    follow_up_questions_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_answer_evaluations_session
        FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
);
