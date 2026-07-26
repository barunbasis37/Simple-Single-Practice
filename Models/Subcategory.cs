namespace SimpleSinglePractice.Models;

public class Subcategory : NamedEntity
{
    public int CategoryId { get; set; }
    public Category? Category { get; set; }
}
