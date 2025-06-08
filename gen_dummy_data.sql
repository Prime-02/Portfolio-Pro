-- Install pgcrypto extension if not already installed
-- This should be run as a superuser or database owner
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enhanced function with proper bcrypt password hashing
CREATE OR REPLACE FUNCTION generate_portfolio_dummy_data(rows_per_table INT) RETURNS VOID AS $$
DECLARE
    table_rec RECORD;
    column_rec RECORD;
    insert_sql TEXT;
    values_sql TEXT;
    col_list TEXT;
    v_user_id UUID;  -- Renamed to avoid ambiguity
    v_project_id UUID;  -- Renamed to avoid ambiguity
    portfolio_id UUID;
    hashed_password TEXT;
    i INT;
    j INT;
BEGIN
    -- Disable triggers temporarily to avoid constraint issues
    PERFORM set_config('session_replication_role', 'replica', true);
    
    -- Clear all existing data first
    PERFORM truncate_tables('portfolio_pro_app');
    
    -- Pre-compute bcrypt hash for 'testpassword' (cost factor 12 for good security)
    -- This is done once to avoid repeated expensive bcrypt operations
    hashed_password := crypt('testpassword', gen_salt('bf', 12));
    
    RAISE NOTICE 'Generated bcrypt hash: %', hashed_password;
    
    -- Generate users with sequential testuserN usernames
    FOR i IN 1..rows_per_table LOOP
        v_user_id := gen_random_uuid();
        
        -- Insert into users table with properly hashed password
        INSERT INTO portfolio_pro_app.users (
            id, email, username, firstname, middlename, lastname, 
            profile_picture, phone_number, is_active, is_visible, 
            role, hashed_password, created_at
        ) VALUES (
            v_user_id,
            'testuser' || i || '@example.com',
            'testuser' || i,
            'First' || i,
            CASE WHEN i%3=0 THEN 'Middle' || i ELSE NULL END,
            'Last' || i,
            CASE WHEN i%4=0 THEN 'https://example.com/profile' || i || '.jpg' ELSE NULL END,
            CASE WHEN i%2=0 THEN '+1' || (3000000000 + i)::TEXT ELSE NULL END,
            TRUE,
            TRUE,
            CASE 
                WHEN i = 1 THEN 'admin' 
                WHEN i%5=0 THEN 'premium' 
                ELSE 'user' 
            END,
            hashed_password,
            NOW() - (random() * INTERVAL '365 days')
        );
        
        -- Insert user settings
        INSERT INTO portfolio_pro_app.user_settings (
            id, language, theme, primary_theme, secondary_theme, 
            layout_style, owner_id
        ) VALUES (
            gen_random_uuid(),
            CASE WHEN i%3=0 THEN 'es' ELSE 'en' END,
            CASE 
                WHEN i%4=0 THEN 'dark' 
                WHEN i%4=1 THEN 'light' 
                ELSE 'custom' 
            END,
            CASE 
                WHEN i%4=0 THEN '#1A1A1A' 
                WHEN i%4=1 THEN '#FFFFFF' 
                ELSE '#000000' 
            END,
            CASE 
                WHEN i%4=0 THEN '#2D2D2D' 
                WHEN i%4=1 THEN '#F5F5F5' 
                ELSE '#FFFFFF' 
            END,
            CASE 
                WHEN i%3=0 THEN 'creative' 
                WHEN i%3=1 THEN 'minimalist' 
                ELSE 'modern' 
            END,
            v_user_id
        );
        
        -- Insert user profile
        INSERT INTO portfolio_pro_app.user_profile (
            id, user_id, github_username, bio, profession, job_title,
            years_of_experience, website_url, location, open_to_work,
            availability, profile_picture, created_at
        ) VALUES (
            gen_random_uuid(),
            v_user_id,
            CASE WHEN i%2=0 THEN 'githubuser' || i ELSE NULL END,
            'This is a sample bio for testuser' || i || '. I have ' || (i%10) || ' years of experience in my field.',
            CASE 
                WHEN i%5=0 THEN 'Software Developer' 
                WHEN i%5=1 THEN 'UX Designer' 
                WHEN i%5=2 THEN 'Data Scientist' 
                WHEN i%5=3 THEN 'Product Manager' 
                ELSE 'Web Developer' 
            END,
            CASE 
                WHEN i%5=0 THEN 'Senior Developer' 
                WHEN i%5=1 THEN 'Lead Designer' 
                WHEN i%5=2 THEN 'Data Analyst' 
                WHEN i%5=3 THEN 'Product Lead' 
                ELSE 'Junior Developer' 
            END,
            i%10,
            CASE WHEN i%3=0 THEN 'https://testuser' || i || '.portfolio.com' ELSE NULL END,
            CASE 
                WHEN i%6=0 THEN 'New York, USA' 
                WHEN i%6=1 THEN 'London, UK' 
                WHEN i%6=2 THEN 'Tokyo, Japan' 
                WHEN i%6=3 THEN 'Berlin, Germany' 
                WHEN i%6=4 THEN 'Sydney, Australia' 
                ELSE 'Remote' 
            END,
            i%3=0,
            CASE 
                WHEN i%4=0 THEN 'Full-time' 
                WHEN i%4=1 THEN 'Part-time' 
                WHEN i%4=2 THEN 'Freelance' 
                ELSE 'Available for projects' 
            END,
            CASE WHEN i%4=0 THEN 'https://example.com/profile' || i || '.jpg' ELSE NULL END,
            NOW() - (random() * INTERVAL '300 days')
        );
        
        -- Insert professional skills (3-5 per user)
        FOR j IN 1..(3 + (i%3)) LOOP
            INSERT INTO portfolio_pro_app.professional_skills (
                id, user_id, skill_name, proficiency_level, created_at
            ) VALUES (
                gen_random_uuid(),
                v_user_id,
                CASE j
                    WHEN 1 THEN 'Python'
                    WHEN 2 THEN 'JavaScript'
                    WHEN 3 THEN 'SQL'
                    WHEN 4 THEN 'React'
                    WHEN 5 THEN 'Docker'
                    ELSE 'Skill' || j
                END,
                CASE (i+j)%5
                    WHEN 0 THEN 'Beginner'
                    WHEN 1 THEN 'Intermediate'
                    WHEN 2 THEN 'Advanced'
                    WHEN 3 THEN 'Expert'
                    ELSE 'Proficient'
                END,
                NOW() - (random() * INTERVAL '200 days')
            );
        END LOOP;
        
        -- Insert social links (2-4 per user)
        FOR j IN 1..(2 + (i%3)) LOOP
            INSERT INTO portfolio_pro_app.social_links (
                id, user_id, platform_name, profile_url, created_at
            ) VALUES (
                gen_random_uuid(),
                v_user_id,
                CASE j
                    WHEN 1 THEN 'LinkedIn'
                    WHEN 2 THEN 'GitHub'
                    WHEN 3 THEN 'Twitter'
                    ELSE 'Personal Website'
                END,
                CASE j
                    WHEN 1 THEN 'https://linkedin.com/in/testuser' || i
                    WHEN 2 THEN 'https://github.com/testuser' || i
                    WHEN 3 THEN 'https://twitter.com/testuser' || i
                    ELSE 'https://testuser' || i || '.com'
                END,
                NOW() - (random() * INTERVAL '150 days')
            );
        END LOOP;
        
        -- Insert education (1-2 per user)
        FOR j IN 1..(1 + (i%2)) LOOP
            INSERT INTO portfolio_pro_app.education (
                id, user_id, institution, degree, field_of_study,
                start_year, end_year, is_current, description
            ) VALUES (
                gen_random_uuid(),
                v_user_id,
                CASE (i+j)%5
                    WHEN 0 THEN 'Harvard University'
                    WHEN 1 THEN 'Stanford University'
                    WHEN 2 THEN 'MIT'
                    WHEN 3 THEN 'University of California'
                    ELSE 'State University'
                END,
                CASE j
                    WHEN 1 THEN 'Bachelor of Science'
                    ELSE 'Master of Science'
                END,
                CASE (i+j)%4
                    WHEN 0 THEN 'Computer Science'
                    WHEN 1 THEN 'Electrical Engineering'
                    WHEN 2 THEN 'Data Science'
                    ELSE 'Information Technology'
                END,
                2010 + (i%10),
                2014 + (i%10) + j,
                j=2 AND i%3=0,
                'Completed degree in ' || CASE (i+j)%4
                    WHEN 0 THEN 'Computer Science'
                    WHEN 1 THEN 'Electrical Engineering'
                    WHEN 2 THEN 'Data Science'
                    ELSE 'Information Technology'
                END
            );
        END LOOP;
        
        -- Create portfolios (1-2 per user)
        FOR j IN 1..(1 + (i%2)) LOOP
            portfolio_id := gen_random_uuid();
            INSERT INTO portfolio_pro_app.portfolios (
                id, user_id, name, slug, description,
                is_public, is_default, cover_image_url, created_at, updated_at
            ) VALUES (
                portfolio_id,
                v_user_id,
                CASE j
                    WHEN 1 THEN 'My Professional Portfolio'
                    ELSE 'Side Projects'
                END,
                'portfolio-' || i || '-' || j || '-' || substring(gen_random_uuid()::text, 1, 8),
                CASE j
                    WHEN 1 THEN 'A collection of my professional work and achievements'
                    ELSE 'Various side projects and experiments'
                END,
                TRUE,
                j=1,
                CASE WHEN i%3=0 THEN 'https://example.com/cover' || i || '-' || j || '.jpg' ELSE NULL END,
                NOW() - (random() * INTERVAL '100 days'),
                NOW() - (random() * INTERVAL '50 days')
            );
        END LOOP;
    END LOOP;
    
    -- Generate projects (more than users to allow sharing)
    FOR i IN 1..(rows_per_table * 2) LOOP
        v_project_id  := gen_random_uuid();
        v_user_id := (SELECT id FROM portfolio_pro_app.users ORDER BY random() LIMIT 1);
        
        INSERT INTO portfolio_pro_app.portfolio_projects (
            id, project_name, project_description, project_category,
            project_url, is_completed, is_concept, project_image_url,
            created_at, is_public
        ) VALUES (
            v_project_id,
            'Project ' || i,
            'This is a detailed description of project ' || i || '. It demonstrates various skills and technologies.',
            CASE i%5
                WHEN 0 THEN 'Web Development'
                WHEN 1 THEN 'Mobile App'
                WHEN 2 THEN 'Data Analysis'
                WHEN 3 THEN 'UI/UX Design'
                ELSE 'Research'
            END,
            CASE WHEN i%3=0 THEN 'https://github.com/projects/project' || i ELSE NULL END,
            i%4 != 0,
            i%5 = 0,
            CASE WHEN i%2=0 THEN 'https://example.com/projects/project' || i || '.jpg' ELSE NULL END,
            NOW() - (random() * INTERVAL '200 days'),
            TRUE
        );
        
        FOR j IN 1..(1 + (i%3)) LOOP
    v_user_id := (SELECT id FROM portfolio_pro_app.users ORDER BY random() LIMIT 1);
    
    INSERT INTO portfolio_pro_app.user_project_association (
    user_id, project_id, role, contribution,
    contribution_description, can_edit, created_at
) VALUES (
    v_user_id,
    v_project_id,
    CASE j
        WHEN 1 THEN 'Lead Developer'
        WHEN 2 THEN 'Designer'
        ELSE 'Contributor'
    END,
    CASE j
        CASE j
        WHEN 1 THEN 'Owner'
        ELSE 'Contributor'
    END,
    CASE j
        WHEN 1 THEN 'Implemented core functionality and database design'
        WHEN 2 THEN 'Created all visual designs and user flows'
        ELSE 'Helped with testing and documentation'
    END,
    j=1,
    NOW() - (random() * INTERVAL '150 days')
) ON CONFLICT (user_id, project_id) DO NOTHING;
END LOOP;
        
        -- Associate project with portfolios (50% chance) - FIXED LINE
        IF i%2 = 0 THEN
            INSERT INTO portfolio_pro_app.portfolio_project_associations (
                portfolio_id, project_id, position, added_at, notes
            ) VALUES (
                (SELECT p.id FROM portfolio_pro_app.portfolios p WHERE p.user_id = v_user_id ORDER BY random() LIMIT 1),
                v_project_id,
                i%10,
                NOW() - (random() * INTERVAL '100 days'),
                CASE WHEN i%3=0 THEN 'Featured project' ELSE NULL END
            );
        END IF;
        
         -- Add project likes (20-50% of projects get likes)
        IF i%4 != 0 THEN
            FOR j IN 1..(1 + (i%5)) LOOP
                INSERT INTO portfolio_pro_app.project_likes (
                    id, project_id, user_id, created_at
                ) VALUES (
                    gen_random_uuid(),
                    v_project_id,
                    (SELECT id FROM portfolio_pro_app.users WHERE id != v_user_id ORDER BY random() LIMIT 1),
                    NOW() - (random() * INTERVAL '90 days')
                );
            END LOOP;
        END IF;
       -- Add project comments (30% of projects get comments)
        IF i%3 = 0 THEN
            FOR j IN 1..(1 + (i%4)) LOOP
                INSERT INTO portfolio_pro_app.project_comments (
                    id, project_id, user_id, content, created_at
                ) VALUES (
                    gen_random_uuid(),
                    v_project_id,
                    (SELECT id FROM portfolio_pro_app.users WHERE id != v_user_id ORDER BY random() LIMIT 1),
                    CASE j
                        WHEN 1 THEN 'Great work on this project! The design is really clean.'
                        WHEN 2 THEN 'I would love to collaborate on something similar.'
                        WHEN 3 THEN 'How did you solve the performance issues?'
                        ELSE 'Impressive results!'
                    END,
                    NOW() - (random() * INTERVAL '80 days')
                );
            END LOOP;
        END IF;
    END LOOP;
    
    -- Generate testimonials (about 1 per 2 users)
    FOR i IN 1..(rows_per_table / 2) LOOP
        v_user_id := (SELECT id FROM portfolio_pro_app.users ORDER BY random() LIMIT 1);
        
        INSERT INTO portfolio_pro_app.testimonials (
            id, user_id, author_user_id, author_name, author_title,
            author_company, author_relationship, content, rating,
            is_approved, created_at
        ) VALUES (
            gen_random_uuid(),
            v_user_id,
            (SELECT id FROM portfolio_pro_app.users WHERE id != v_user_id ORDER BY random() LIMIT 1),
            'Author ' || i,
            CASE i%4
                WHEN 0 THEN 'Senior Developer'
                WHEN 1 THEN 'Product Manager'
                WHEN 2 THEN 'CTO'
                ELSE 'Colleague'
            END,
            CASE i%5
                WHEN 0 THEN 'Tech Corp'
                WHEN 1 THEN 'Design Studio'
                WHEN 2 THEN 'Data Insights'
                WHEN 3 THEN 'Web Solutions'
                ELSE 'Innovate Co'
            END,
            CASE i%3
                WHEN 0 THEN 'Former Manager'
                WHEN 1 THEN 'Colleague'
                ELSE 'Client'
            END,
            'I had the pleasure of working with this professional and can attest to their ' ||
            CASE i%4
                WHEN 0 THEN 'technical skills and problem-solving abilities.'
                WHEN 1 THEN 'creativity and attention to detail.'
                WHEN 2 THEN 'leadership and team collaboration.'
                ELSE 'dedication and work ethic.'
            END,
            4 + (i%2),
            TRUE,
            NOW() - (random() * INTERVAL '120 days')
        );
    END LOOP;
    
    -- Generate custom sections and items (for about 50% of users)
    FOR v_user_id IN 
  SELECT id FROM portfolio_pro_app.users 
  WHERE mod(abs(hashtext(id::text)), 2) = 0 
LOOP
        DECLARE
            section_id UUID;
        BEGIN
            -- Create 2-4 custom sections per selected user
              FOR j IN 1..(2 + mod(abs(hashtext(v_user_id::text)), 3)) LOOP
                section_id := gen_random_uuid();
                
                INSERT INTO portfolio_pro_app.custom_sections (
                    id, user_id, section_type, title, description,
                    position, is_visible
                ) VALUES (
                    section_id,
                    v_user_id,
                    CASE j
                        WHEN 1 THEN 'experience'
                        WHEN 2 THEN 'publications'
                        ELSE 'achievements'
                    END,
                    CASE j
                        WHEN 1 THEN 'Work Experience'
                        WHEN 2 THEN 'Publications'
                        ELSE 'Awards'
                    END,
                    CASE j
                        WHEN 1 THEN 'My professional work history'
                        WHEN 2 THEN 'Articles and papers I''ve published'
                        ELSE 'Recognition I''ve received'
                    END,
                    j,
                    TRUE
                );
                
                -- Add 2-5 items per section
                FOR k IN 1..(2 + mod(abs(hashtext(v_user_id::text)), 3)) LOOP
                    INSERT INTO portfolio_pro_app.custom_section_items (
                        id, section_id, title, subtitle, description,
                        start_date, end_date, is_current, media_url
                    ) VALUES (
                        gen_random_uuid(),
                        section_id,
                        CASE j
                            WHEN 1 THEN 'Job Position ' || k
                            WHEN 2 THEN 'Publication ' || k
                            ELSE 'Award ' || k
                        END,
                        CASE j
                            WHEN 1 THEN 'Company ' || k
                            WHEN 2 THEN 'Journal ' || k
                            ELSE 'Organization ' || k
                        END,
                        CASE j
                            WHEN 1 THEN 'Responsibilities included...'
                            WHEN 2 THEN 'Published in...'
                            ELSE 'Received for...'
                        END,
                        NOW() - (random() * INTERVAL '365 days' * (k+1)),
                        CASE WHEN k%2=0 THEN NOW() - (random() * INTERVAL '365 days' * k) ELSE NULL END,
                        k=1 AND j=1,
                        CASE WHEN k%3=0 THEN 'https://example.com/media/' || k || '.jpg' ELSE NULL END
                    );
                END LOOP;
            END LOOP;
        END;
    END LOOP;
    
    -- Generate content blocks (for about 30% of users)
	FOR v_user_id IN 
	  SELECT id FROM portfolio_pro_app.users 
	  WHERE mod(abs(hashtext(id::text)), 3) = 0 
	LOOP
        -- Create 1-3 content blocks per selected user
        FOR j IN 1..(1 + mod(abs(hashtext(v_user_id::text)), 3)) LOOP
            INSERT INTO portfolio_pro_app.content_blocks (
                id, user_id, block_type, title, content,
                position, is_visible
            ) VALUES (
                gen_random_uuid(),
                v_user_id,
                CASE j
                    WHEN 1 THEN 'about'
                    WHEN 2 THEN 'services'
                    ELSE 'contact'
                END,
                CASE j
                    WHEN 1 THEN 'About Me'
                    WHEN 2 THEN 'My Services'
                    ELSE 'Contact Info'
                END,
                CASE j
                    WHEN 1 THEN 'I am a professional with extensive experience in...'
                    WHEN 2 THEN 'I offer the following services: ...'
                    ELSE 'You can reach me at: ...'
                END,
                j,
                TRUE
            );
        END LOOP;
    END LOOP;
    
    -- Generate media gallery items (for about 70% of users)
	FOR v_user_id IN 
	  SELECT id FROM portfolio_pro_app.users 
	  WHERE mod(abs(hashtext(id::text)), 10) < 7 
	LOOP
        -- Create 2-6 media items per selected user
        FOR j IN 1..(2 + mod(abs(hashtext(v_user_id::text)), 5)) LOOP
            INSERT INTO portfolio_pro_app.media_gallery (
                id, user_id, media_type, url, title,
                description, is_featured, created_at
            ) VALUES (
                gen_random_uuid(),
                v_user_id,
                CASE j%3
                    WHEN 0 THEN 'image'
                    WHEN 1 THEN 'video'
                    ELSE 'document'
                END,
                'https://example.com/media/user_' || (v_user_id::text) || '_' || j || 
                CASE j%3
                    WHEN 0 THEN '.jpg'
                    WHEN 1 THEN '.mp4'
                    ELSE '.pdf'
                END,
                CASE j%4
                    WHEN 0 THEN 'Project Screenshot'
                    WHEN 1 THEN 'Demo Video'
                    WHEN 2 THEN 'Presentation'
                    ELSE 'Documentation'
                END,
                CASE j%4
                    WHEN 0 THEN 'Screenshot from my latest project'
                    WHEN 1 THEN 'Video demonstration of features'
                    WHEN 2 THEN 'Slide deck presentation'
                    ELSE 'Technical documentation'
                END,
                j=1,
                NOW() - (random() * INTERVAL '180 days')
            );
        END LOOP;
    END LOOP;
    
    -- Generate certifications (for about 60% of users)
FOR v_user_id IN 
  SELECT id FROM portfolio_pro_app.users 
  WHERE mod(abs(hashtext(id::text)), 10) < 6 
LOOP
    -- Create 1-3 certifications per selected user
    FOR j IN 1..(1 + mod(abs(hashtext(v_user_id::text)), 3)) LOOP
        INSERT INTO portfolio_pro_app.certifications (
            id, user_id, certification_name, issuing_organization,
            issue_date, expiration_date, created_at
        ) VALUES (
            gen_random_uuid(),
            v_user_id,
            CASE j
                WHEN 1 THEN 'Certified Developer'
                WHEN 2 THEN 'UX Design Professional'
                ELSE 'Data Science Specialist'
            END,
            CASE j
                WHEN 1 THEN 'Technology Institute'
                WHEN 2 THEN 'Design Association'
                ELSE 'Data Science Council'
            END,
            NOW() - (random() * INTERVAL '365 days' * 2),
            CASE WHEN j%2=0 THEN NOW() + (random() * INTERVAL '365 days') ELSE NULL END,
            NOW() - (random() * INTERVAL '300 days')
        );
    END LOOP;
END LOOP;
    
   -- Generate user devices (for about 80% of users)
FOR v_user_id IN 
  SELECT id FROM portfolio_pro_app.users 
  WHERE mod(abs(hashtext(id::text)), 10) < 8 
LOOP
    -- Create 1-3 devices per selected user
    FOR j IN 1..(1 + mod(abs(hashtext(v_user_id::text)), 3)) LOOP
        INSERT INTO portfolio_pro_app.user_devices (
            id, user_id, device_name, device_type, last_used
        ) VALUES (
            gen_random_uuid(),
            v_user_id,
            CASE j
                WHEN 1 THEN 'Primary Laptop'
                WHEN 2 THEN 'Smartphone'
                ELSE 'Tablet'
            END,
            CASE j
                WHEN 1 THEN 'Laptop'
                WHEN 2 THEN 'Phone'
                ELSE 'Tablet'
            END,
            NOW() - (random() * INTERVAL '30 days')
        );
    END LOOP;
END LOOP;
    
    -- Re-enable triggers
    PERFORM set_config('session_replication_role', 'origin', true);
    
    RAISE NOTICE 'Successfully generated dummy data for % tables with % rows per user table', 
        (SELECT count(*) FROM pg_tables WHERE schemaname = 'portfolio_pro_app'),
        rows_per_table;
    RAISE NOTICE 'All test users have password: testpassword (bcrypt hashed)';
END;
$$ LANGUAGE plpgsql;

-- Helper function to truncate all tables (unchanged)
CREATE OR REPLACE FUNCTION truncate_tables(schema_name TEXT) RETURNS VOID AS $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = schema_name
    LOOP
        EXECUTE format('TRUNCATE TABLE %I.%I CASCADE', schema_name, t.tablename);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Utility function to create different user types with specific passwords
CREATE OR REPLACE FUNCTION create_test_user_with_password(
    username_suffix TEXT,
    plain_password TEXT,
    user_role TEXT DEFAULT 'user'
) RETURNS UUID AS $$
DECLARE
    v_user_id UUID;  -- Renamed to avoid ambiguity
    hashed_password TEXT;
BEGIN
    v_user_id := gen_random_uuid();
    hashed_password := crypt(plain_password, gen_salt('bf', 12));
    
    INSERT INTO portfolio_pro_app.users (
        id, email, username, firstname, lastname, 
        is_active, is_visible, role, hashed_password, created_at
    ) VALUES (
        v_user_id,
        'test' || username_suffix || '@example.com',
        'test' || username_suffix,
        'Test',
        'User' || username_suffix,
        TRUE,
        TRUE,
        user_role,
        hashed_password,
        NOW()
    );
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;