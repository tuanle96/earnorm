"""Integration tests for model relationships.

This module tests relationship functionality including:
- Many-to-One relationships
- One-to-Many relationships  
- Many-to-Many relationships
- Relationship field validation
- Relationship queries and joins
- Cascade operations
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from earnorm.base.model.base import BaseModel
from earnorm.base.env import Environment
from earnorm.fields.primitive.string import StringField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.object_id import ObjectIdField
from earnorm.fields.relations.many_to_one import ManyToOneField
from earnorm.fields.relations.one_to_many import OneToManyField
from earnorm.fields.relations.many_to_many import ManyToManyField
from earnorm.exceptions import ValidationError, DatabaseError


# Test Models for Relationship Testing
class Category(BaseModel):
    """Category model for relationship testing."""
    
    _name = "category"
    
    name = StringField(required=True, max_length=100)
    description = StringField(max_length=500)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class Author(BaseModel):
    """Author model for relationship testing."""
    
    _name = "author"
    
    name = StringField(required=True, max_length=100)
    email = StringField(required=True, max_length=255)
    bio = StringField(max_length=1000)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class Book(BaseModel):
    """Book model with relationships."""
    
    _name = "book"
    
    title = StringField(required=True, max_length=200)
    isbn = StringField(required=True, max_length=20)
    pages = IntegerField(min_value=1)
    published_date = DateTimeField()
    active = BooleanField(default=True)
    
    # Many-to-One: Many books belong to one category
    category_id = ManyToOneField("Category", required=True)
    
    # Many-to-One: Many books belong to one primary author
    author_id = ManyToOneField("Author", required=True)
    
    created_at = DateTimeField(auto_now_add=True)


class Review(BaseModel):
    """Review model for One-to-Many relationship testing."""
    
    _name = "review"
    
    title = StringField(required=True, max_length=100)
    content = StringField(required=True, max_length=2000)
    rating = IntegerField(min_value=1, max_value=5, required=True)
    reviewer_name = StringField(required=True, max_length=100)
    
    # Many-to-One: Many reviews belong to one book
    book_id = ManyToOneField("Book", required=True)
    
    created_at = DateTimeField(auto_now_add=True)


class Tag(BaseModel):
    """Tag model for Many-to-Many relationship testing."""
    
    _name = "tag"
    
    name = StringField(required=True, max_length=50)
    description = StringField(max_length=200)
    color = StringField(max_length=7, default="#000000")  # Hex color
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class BookTag(BaseModel):
    """Junction model for Book-Tag Many-to-Many relationship."""
    
    _name = "book_tag"
    
    book_id = ManyToOneField("Book", required=True)
    tag_id = ManyToOneField("Tag", required=True)
    created_at = DateTimeField(auto_now_add=True)


class TestRelationshipBase:
    """Base class for relationship testing."""
    
    @pytest.fixture
    async def mock_env(self):
        """Create a mock environment with database adapter."""
        env = MagicMock(spec=Environment)
        env._initialized = True
        env.container = MagicMock()
        env.config = MagicMock()
        
        # Mock database adapter
        adapter = AsyncMock()
        env.adapter = adapter
        
        return env
    
    @pytest.fixture
    def sample_category_data(self):
        """Sample category data."""
        return {
            "name": "Science Fiction",
            "description": "Books about future technology and space",
            "active": True
        }
    
    @pytest.fixture
    def sample_author_data(self):
        """Sample author data."""
        return {
            "name": "Isaac Asimov",
            "email": "isaac@example.com",
            "bio": "Famous science fiction author",
            "active": True
        }
    
    @pytest.fixture
    def sample_book_data(self):
        """Sample book data."""
        return {
            "title": "Foundation",
            "isbn": "978-0553293357",
            "pages": 244,
            "published_date": datetime(1951, 5, 1),
            "category_id": "507f1f77bcf86cd799439011",
            "author_id": "507f1f77bcf86cd799439012",
            "active": True
        }
    
    @pytest.fixture
    def sample_review_data(self):
        """Sample review data."""
        return {
            "title": "Great Book!",
            "content": "This is an excellent science fiction novel.",
            "rating": 5,
            "reviewer_name": "John Reader",
            "book_id": "507f1f77bcf86cd799439013"
        }
    
    @pytest.fixture
    def sample_tag_data(self):
        """Sample tag data."""
        return {
            "name": "Classic",
            "description": "Classic literature",
            "color": "#FF5733",
            "active": True
        }


class TestManyToOneRelationships(TestRelationshipBase):
    """Test Many-to-One relationship functionality."""
    
    @pytest.mark.asyncio
    async def test_create_book_with_category_relationship(self, mock_env, sample_book_data):
        """Test creating a book with category relationship."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439013"
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            with patch.object(Book, '_convert_to_db', return_value=sample_book_data):
                result = await Book.create(sample_book_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is a Book recordset
                assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_create_book_with_author_relationship(self, mock_env, sample_book_data):
        """Test creating a book with author relationship."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439013"
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            with patch.object(Book, '_convert_to_db', return_value=sample_book_data):
                result = await Book.create(sample_book_data)
                
                # Verify result is a Book recordset
                assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_search_books_by_category(self, mock_env):
        """Test searching books by category relationship."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            result = await Book.search([("category_id", "=", "507f1f77bcf86cd799439011")])
            
            # Verify result is a Book recordset
            assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_search_books_by_author(self, mock_env):
        """Test searching books by author relationship."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            result = await Book.search([("author_id", "=", "507f1f77bcf86cd799439012")])
            
            # Verify result is a Book recordset
            assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_create_review_with_book_relationship(self, mock_env, sample_review_data):
        """Test creating a review with book relationship."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439014"
        
        with patch.object(Review, '_get_env', return_value=mock_env):
            with patch.object(Review, '_convert_to_db', return_value=sample_review_data):
                result = await Review.create(sample_review_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is a Review recordset
                assert isinstance(result, Review)


class TestOneToManyRelationships(TestRelationshipBase):
    """Test One-to-Many relationship functionality."""
    
    @pytest.mark.asyncio
    async def test_search_reviews_for_book(self, mock_env):
        """Test searching all reviews for a specific book (One-to-Many)."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Review, '_get_env', return_value=mock_env):
            # Search all reviews for a specific book
            result = await Review.search([("book_id", "=", "507f1f77bcf86cd799439013")])
            
            # Verify result is a Review recordset
            assert isinstance(result, Review)
    
    @pytest.mark.asyncio
    async def test_search_books_for_category(self, mock_env):
        """Test searching all books in a category (One-to-Many)."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            # Search all books in a specific category
            result = await Book.search([("category_id", "=", "507f1f77bcf86cd799439011")])
            
            # Verify result is a Book recordset
            assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_search_books_for_author(self, mock_env):
        """Test searching all books by an author (One-to-Many)."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            # Search all books by a specific author
            result = await Book.search([("author_id", "=", "507f1f77bcf86cd799439012")])
            
            # Verify result is a Book recordset
            assert isinstance(result, Book)


class TestManyToManyRelationships(TestRelationshipBase):
    """Test Many-to-Many relationship functionality through junction model."""
    
    @pytest.mark.asyncio
    async def test_create_book_tag_relationship(self, mock_env):
        """Test creating a book-tag relationship."""
        relationship_data = {
            "book_id": "507f1f77bcf86cd799439013",
            "tag_id": "507f1f77bcf86cd799439015"
        }
        
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439016"
        
        with patch.object(BookTag, '_get_env', return_value=mock_env):
            with patch.object(BookTag, '_convert_to_db', return_value=relationship_data):
                result = await BookTag.create(relationship_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is a BookTag recordset
                assert isinstance(result, BookTag)
    
    @pytest.mark.asyncio
    async def test_search_tags_for_book(self, mock_env):
        """Test searching all tags for a specific book."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(BookTag, '_get_env', return_value=mock_env):
            # Search all book-tag relationships for a specific book
            result = await BookTag.search([("book_id", "=", "507f1f77bcf86cd799439013")])
            
            # Verify result is a BookTag recordset
            assert isinstance(result, BookTag)
    
    @pytest.mark.asyncio
    async def test_search_books_for_tag(self, mock_env):
        """Test searching all books with a specific tag."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(BookTag, '_get_env', return_value=mock_env):
            # Search all book-tag relationships for a specific tag
            result = await BookTag.search([("tag_id", "=", "507f1f77bcf86cd799439015")])
            
            # Verify result is a BookTag recordset
            assert isinstance(result, BookTag)
    
    @pytest.mark.asyncio
    async def test_remove_book_tag_relationship(self, mock_env):
        """Test removing a book-tag relationship."""
        # Create book-tag instance
        book_tag = BookTag(env=mock_env)
        book_tag._ids = ("507f1f77bcf86cd799439016",)
        
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.delete.return_value = 1
        
        with patch.object(book_tag, '_unlink', return_value=None):
            result = await book_tag.unlink()
            
            assert result is True


class TestRelationshipValidation(TestRelationshipBase):
    """Test relationship field validation."""
    
    @pytest.mark.asyncio
    async def test_many_to_one_field_creation(self):
        """Test creating Many-to-One field."""
        field = ManyToOneField("Category", required=True)
        
        assert isinstance(field, ManyToOneField)
        assert field.required is True
        assert hasattr(field, 'comodel_name')
    
    @pytest.mark.asyncio
    async def test_one_to_many_field_creation(self):
        """Test creating One-to-Many field."""
        field = OneToManyField("Review", inverse_name="book_id")
        
        assert isinstance(field, OneToManyField)
        assert hasattr(field, 'comodel_name')
        assert hasattr(field, 'inverse_name')
    
    @pytest.mark.asyncio
    async def test_many_to_many_field_creation(self):
        """Test creating Many-to-Many field."""
        field = ManyToManyField("Tag", relation="book_tag", column1="book_id", column2="tag_id")
        
        assert isinstance(field, ManyToManyField)
        assert hasattr(field, 'comodel_name')
        assert hasattr(field, 'relation')
    
    @pytest.mark.asyncio
    async def test_relationship_field_validation(self, mock_env):
        """Test relationship field validation."""
        # Test valid ObjectId for relationship
        field = ManyToOneField("Category", required=True)
        
        # Valid ObjectId should pass validation
        result = await field.validate("507f1f77bcf86cd799439011")
        assert result == "507f1f77bcf86cd799439011"
    
    @pytest.mark.asyncio
    async def test_relationship_field_none_optional(self, mock_env):
        """Test relationship field with None when optional."""
        field = ManyToOneField("Category", required=False)
        
        result = await field.validate(None)
        assert result is None


class TestComplexRelationshipQueries(TestRelationshipBase):
    """Test complex queries involving relationships."""
    
    @pytest.mark.asyncio
    async def test_search_books_with_multiple_relationship_filters(self, mock_env):
        """Test searching books with multiple relationship filters."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Book, '_get_env', return_value=mock_env):
            # Search books by both category and author
            result = await Book.search([
                ("category_id", "=", "507f1f77bcf86cd799439011"),
                ("author_id", "=", "507f1f77bcf86cd799439012"),
                ("active", "=", True)
            ])
            
            # Verify result is a Book recordset
            assert isinstance(result, Book)
    
    @pytest.mark.asyncio
    async def test_search_reviews_with_rating_and_book_filter(self, mock_env):
        """Test searching reviews with rating and book filters."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Review, '_get_env', return_value=mock_env):
            # Search high-rated reviews for a specific book
            result = await Review.search([
                ("book_id", "=", "507f1f77bcf86cd799439013"),
                ("rating", ">=", 4)
            ])
            
            # Verify result is a Review recordset
            assert isinstance(result, Review)


class TestRelationshipErrorHandling(TestRelationshipBase):
    """Test error handling in relationship operations."""

    @pytest.mark.asyncio
    async def test_create_book_with_invalid_category_id(self, mock_env):
        """Test creating book with invalid category ID."""
        invalid_data = {
            "title": "Test Book",
            "isbn": "978-0000000000",
            "category_id": "invalid_id",  # Invalid ObjectId
            "author_id": "507f1f77bcf86cd799439012"
        }

        with patch.object(Book, '_get_env', return_value=mock_env):
            # Should raise validation error for invalid ObjectId
            with pytest.raises((ValidationError, ValueError)):
                await Book.create(invalid_data)

    @pytest.mark.asyncio
    async def test_create_review_without_required_book_id(self, mock_env):
        """Test creating review without required book ID."""
        invalid_data = {
            "title": "Great Review",
            "content": "This is a great book!",
            "rating": 5,
            "reviewer_name": "John Doe"
            # Missing required book_id
        }

        with patch.object(Review, '_get_env', return_value=mock_env):
            # Should raise validation error for missing required field
            with pytest.raises((ValidationError, ValueError)):
                await Review.create(invalid_data)

    @pytest.mark.asyncio
    async def test_relationship_database_error(self, mock_env):
        """Test handling database errors in relationship operations."""
        # Mock adapter to raise database error
        adapter = mock_env.adapter
        adapter.create.side_effect = DatabaseError("Foreign key constraint failed", backend="mongodb")

        relationship_data = {
            "book_id": "507f1f77bcf86cd799439013",
            "tag_id": "507f1f77bcf86cd799439015"
        }

        with patch.object(BookTag, '_get_env', return_value=mock_env):
            with patch.object(BookTag, '_convert_to_db', return_value=relationship_data):
                with pytest.raises(DatabaseError) as exc_info:
                    await BookTag.create(relationship_data)

                assert "Foreign key constraint failed" in str(exc_info.value)
                assert exc_info.value.backend == "mongodb"


class TestAdvancedRelationshipScenarios(TestRelationshipBase):
    """Test advanced relationship scenarios and workflows."""

    @pytest.mark.asyncio
    async def test_complete_book_creation_workflow(self, mock_env, sample_category_data, sample_author_data, sample_book_data):
        """Test complete workflow: create category, author, then book."""
        adapter = mock_env.adapter
        adapter.create.side_effect = [
            "507f1f77bcf86cd799439011",  # category_id
            "507f1f77bcf86cd799439012",  # author_id
            "507f1f77bcf86cd799439013"   # book_id
        ]

        with patch.object(Category, '_get_env', return_value=mock_env):
            with patch.object(Author, '_get_env', return_value=mock_env):
                with patch.object(Book, '_get_env', return_value=mock_env):
                    with patch.object(Category, '_convert_to_db', return_value=sample_category_data):
                        with patch.object(Author, '_convert_to_db', return_value=sample_author_data):
                            with patch.object(Book, '_convert_to_db', return_value=sample_book_data):
                                # Create category first
                                category = await Category.create(sample_category_data)
                                assert isinstance(category, Category)

                                # Create author
                                author = await Author.create(sample_author_data)
                                assert isinstance(author, Author)

                                # Create book with relationships
                                book = await Book.create(sample_book_data)
                                assert isinstance(book, Book)

                                # Verify all creates were called
                                assert adapter.create.call_count == 3

    @pytest.mark.asyncio
    async def test_book_with_multiple_reviews_workflow(self, mock_env, sample_book_data):
        """Test creating a book and adding multiple reviews."""
        adapter = mock_env.adapter
        adapter.create.side_effect = [
            "507f1f77bcf86cd799439013",  # book_id
            "507f1f77bcf86cd799439014",  # review_1_id
            "507f1f77bcf86cd799439015",  # review_2_id
            "507f1f77bcf86cd799439016"   # review_3_id
        ]

        review_data_1 = {
            "title": "Excellent!",
            "content": "Amazing book, highly recommended!",
            "rating": 5,
            "reviewer_name": "Alice",
            "book_id": "507f1f77bcf86cd799439013"
        }

        review_data_2 = {
            "title": "Good read",
            "content": "Enjoyed this book, good story.",
            "rating": 4,
            "reviewer_name": "Bob",
            "book_id": "507f1f77bcf86cd799439013"
        }

        review_data_3 = {
            "title": "Okay",
            "content": "It was alright, not my favorite.",
            "rating": 3,
            "reviewer_name": "Charlie",
            "book_id": "507f1f77bcf86cd799439013"
        }

        with patch.object(Book, '_get_env', return_value=mock_env):
            with patch.object(Review, '_get_env', return_value=mock_env):
                with patch.object(Book, '_convert_to_db', return_value=sample_book_data):
                    with patch.object(Review, '_convert_to_db', side_effect=[review_data_1, review_data_2, review_data_3]):
                        # Create book
                        book = await Book.create(sample_book_data)
                        assert isinstance(book, Book)

                        # Add multiple reviews
                        review1 = await Review.create(review_data_1)
                        review2 = await Review.create(review_data_2)
                        review3 = await Review.create(review_data_3)

                        assert isinstance(review1, Review)
                        assert isinstance(review2, Review)
                        assert isinstance(review3, Review)

                        # Verify all creates were called
                        assert adapter.create.call_count == 4

    @pytest.mark.asyncio
    async def test_book_with_multiple_tags_workflow(self, mock_env, sample_book_data, sample_tag_data):
        """Test creating a book and associating it with multiple tags."""
        adapter = mock_env.adapter
        adapter.create.side_effect = [
            "507f1f77bcf86cd799439013",  # book_id
            "507f1f77bcf86cd799439015",  # tag_1_id
            "507f1f77bcf86cd799439016",  # tag_2_id
            "507f1f77bcf86cd799439017",  # book_tag_1_id
            "507f1f77bcf86cd799439018"   # book_tag_2_id
        ]

        tag_data_1 = {
            "name": "Classic",
            "description": "Classic literature",
            "color": "#FF5733",
            "active": True
        }

        tag_data_2 = {
            "name": "Sci-Fi",
            "description": "Science fiction genre",
            "color": "#33FF57",
            "active": True
        }

        book_tag_data_1 = {
            "book_id": "507f1f77bcf86cd799439013",
            "tag_id": "507f1f77bcf86cd799439015"
        }

        book_tag_data_2 = {
            "book_id": "507f1f77bcf86cd799439013",
            "tag_id": "507f1f77bcf86cd799439016"
        }

        with patch.object(Book, '_get_env', return_value=mock_env):
            with patch.object(Tag, '_get_env', return_value=mock_env):
                with patch.object(BookTag, '_get_env', return_value=mock_env):
                    with patch.object(Book, '_convert_to_db', return_value=sample_book_data):
                        with patch.object(Tag, '_convert_to_db', side_effect=[tag_data_1, tag_data_2]):
                            with patch.object(BookTag, '_convert_to_db', side_effect=[book_tag_data_1, book_tag_data_2]):
                                # Create book
                                book = await Book.create(sample_book_data)
                                assert isinstance(book, Book)

                                # Create tags
                                tag1 = await Tag.create(tag_data_1)
                                tag2 = await Tag.create(tag_data_2)

                                assert isinstance(tag1, Tag)
                                assert isinstance(tag2, Tag)

                                # Create relationships
                                book_tag1 = await BookTag.create(book_tag_data_1)
                                book_tag2 = await BookTag.create(book_tag_data_2)

                                assert isinstance(book_tag1, BookTag)
                                assert isinstance(book_tag2, BookTag)

                                # Verify all creates were called
                                assert adapter.create.call_count == 5
