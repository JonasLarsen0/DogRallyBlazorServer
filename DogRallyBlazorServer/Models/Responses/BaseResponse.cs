namespace DogRallyBlazorServer.Models.Responses;

public class BaseResponse //Used to give feedback to the user based on status code.
{
    public int StatusCode { get; set; }
    public string Message { get; set; }
}
