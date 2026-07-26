using SimpleSinglePractice.Models;
using Xunit;

namespace SimpleSinglePractice.Tests;

public class ModelTests
{
    [Fact]
    public void Category_DefaultsNameToEmptyString()
    {
        var category = new Category();

        Assert.Equal(string.Empty, category.Name);
        Assert.Null(category.Description);
    }

    [Fact]
    public void Category_StoresAssignedValues()
    {
        var category = new Category { Id = 1, Name = "Electronics", Description = "Gadgets" };

        Assert.Equal(1, category.Id);
        Assert.Equal("Electronics", category.Name);
        Assert.Equal("Gadgets", category.Description);
    }

    [Fact]
    public void Subcategory_DefaultsNameToEmptyString()
    {
        var subcategory = new Subcategory();

        Assert.Equal(string.Empty, subcategory.Name);
        Assert.Null(subcategory.Description);
    }

    [Fact]
    public void Subcategory_LinksToParentCategoryViaForeignKey()
    {
        var category = new Category { Id = 1, Name = "Electronics" };
        var subcategory = new Subcategory
        {
            Id = 10,
            Name = "Phones",
            CategoryId = category.Id,
            Category = category,
        };

        Assert.Equal(category.Id, subcategory.CategoryId);
        Assert.Same(category, subcategory.Category);
    }
}
