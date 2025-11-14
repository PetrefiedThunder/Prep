SELECT *
FROM verification_tasks
WHERE status = 'pending'
ORDER BY due_at ASC;
